import argparse
import subprocess
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "outputs"


def buscar_soffice():
    posibles = [
        "soffice",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]

    for exe in posibles:
        try:
            result = subprocess.run(
                [exe, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return exe
        except Exception:
            pass

    raise FileNotFoundError("No encontré LibreOffice. Instala LibreOffice para exportar a PDF.")


def convertir_a_pdf(excel_path):
    excel_path = Path(excel_path).resolve()

    if not excel_path.exists():
        raise FileNotFoundError(f"No existe: {excel_path}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    soffice = buscar_soffice()

    cmd = [
        soffice,
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(OUTPUT_DIR.resolve()),
        str(excel_path)
    ]

    subprocess.run(cmd, check=True)

    pdf = OUTPUT_DIR / (excel_path.stem + ".pdf")

    print("PDF LISTO")
    print(f"Archivo creado: {pdf}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("excel", type=str)
    args = parser.parse_args()

    convertir_a_pdf(args.excel)


if __name__ == "__main__":
    main()
