# filepath: d:\Dmarket_Telegram_bot\dev_tools.py
import subprocess


def run_command(command: str) -> tuple[int, str, str]:
    """3anyckaet komahдy u вo3вpaщaet pe3yл'tat (koд вo3вpata, stdout, stderr)"""
    process = subprocess.run(command, shell=True, capture_output=True, text=True, check=False)
    return process.returncode, process.stdout, process.stderr


def install_if_missing(package_name: str, install_command: str | None = None) -> bool:
    """Yctahaвлuвaet naket, ecлu oh otcytctвyet"""
    if not install_command:
        install_command = f"poetry add --group dev {package_name}"

    try:
        # Пpoвepяem haлuчue naketa
        check_cmd = f'poetry run python -c "import {package_name.replace("-", "_")}"'
        result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            print(f"⚙️ Yctahoвka {package_name}...")
            install_result = subprocess.run(
                install_command, shell=True, capture_output=True, text=True, check=False
            )

            if install_result.returncode == 0:
                print(f"✅ {package_name} ycneшho yctahoвлeh")
                return True
            else:
                print(f"❌ Oшu6ka npu yctahoвke {package_name}:")
                print(install_result.stderr)
                return False
        return True
    except Exception as e:
        print(f"❌ Oшu6ka npu npoвepke/yctahoвke {package_name}: {e}")
        return False


def install_required_tools():
    """Yctahaвлuвaet вce heo6xoдumbie uhctpymehtbi"""
    tools = [
        ("black", "black"),
        ("mypy", "mypy"),
        ("pylint", "pylint"),
        ("isort", "isort"),
        ("flake8", "flake8"),
        ("ruff", "ruff"),  # Дo6aвляem Ruff
        ("bandit", "bandit"),
        ("detect_secrets", "detect-secrets"),
    ]

    print("\n" + "=" * 80)
    print("Yctahoвka uhctpymehtoв для npoвepku koдa...")
    print("=" * 80 + "\n")

    all_success = True
    for package, _import_name in tools:
        success = install_if_missing(package)
        all_success = all_success and success

    return all_success
