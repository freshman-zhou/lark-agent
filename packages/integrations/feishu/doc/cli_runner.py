import asyncio
import shlex
from dataclasses import dataclass

from packages.shared.config import get_settings
from packages.shared.exceptions import FeishuApiException


@dataclass
class CliResult:
    args: list[str]
    stdout: str
    stderr: str
    returncode: int


class FeishuDocCliRunner:
    """Runs configured Feishu document CLI commands.

    The rest of the application should call domain-shaped document methods
    instead of building arbitrary shell commands.
    """

    def __init__(self):
        self.settings = get_settings()

    async def run_template(
        self,
        template: str,
        values: dict[str, str],
        timeout_seconds: int | None = None,
    ) -> CliResult:
        if not template.strip():
            raise FeishuApiException(
                message="Feishu document CLI command template is empty",
                detail={"template": template},
            )

        command = self._render_command(template, values)
        args = shlex.split(command)

        if not args:
            raise FeishuApiException(
                message="Feishu document CLI command is empty after rendering",
                detail={"template": template},
            )

        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds or self.settings.feishu_doc_cli_timeout,
            )
        except TimeoutError as exc:
            process.kill()
            await process.wait()
            raise FeishuApiException(
                message="Feishu document CLI command timed out",
                detail={
                    "args": self._safe_args(args),
                    "timeout": timeout_seconds or self.settings.feishu_doc_cli_timeout,
                },
            ) from exc

        stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
        stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
        result = CliResult(
            args=self._safe_args(args),
            stdout=stdout,
            stderr=stderr,
            returncode=process.returncode or 0,
        )

        if result.returncode != 0:
            raise FeishuApiException(
                message="Feishu document CLI command failed",
                detail={
                    "args": result.args,
                    "returncode": result.returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                },
            )

        return result

    @staticmethod
    def _render_command(template: str, values: dict[str, str]) -> str:
        rendered_values = {
            key: shlex.quote(str(value or ""))
            for key, value in values.items()
        }
        return template.format(**rendered_values)

    @staticmethod
    def _safe_args(args: list[str]) -> list[str]:
        secret_keys = {"--app-secret", "--secret", "--token", "--access-token"}
        safe_args: list[str] = []
        mask_next = False

        for arg in args:
            if mask_next:
                safe_args.append("***")
                mask_next = False
                continue

            if arg in secret_keys:
                safe_args.append(arg)
                mask_next = True
                continue

            if any(part in arg.lower() for part in ["secret=", "token=", "password="]):
                key = arg.split("=", 1)[0]
                safe_args.append(f"{key}=***")
                continue

            safe_args.append(arg)

        return safe_args
