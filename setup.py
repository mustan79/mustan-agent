from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mustan-agent",
    version="3.3.0",
    author="Mustafa Tan",
    description="Otonom Yazılım Geliştirme ve Mimari Asistanı (v3.3 PRO)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mustan79/mustan-agent",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    python_requires=">=3.10",
    # Ajanın çalışması için zorunlu olan ana paketler
    install_requires=[
        "google-genai>=0.1.0",
        "openai>=1.0.0",
        "pydantic>=2.0.0",
        "keyring>=24.0.0",
        "playwright>=1.40.0",
        "SpeechRecognition>=3.10.0",
        "PyAudio>=0.2.14",
        "PyYAML>=6.0",
        "websockets>=12.0",      # MustanBridge için
        "pyautogui>=0.9.54",     # Otonom bilgisayar kullanımı için
        "Pillow>=10.0.0",        # Ekran okuma (Vision) için
        "keyboard>=0.13.5",      # ESC acil durum freni için
        "pyttsx3>=2.90"          # Memocan (Sesli asistan) için
    ],
    # Sadece test ortamında (TDD) kurulacak paketler
    extras_require={
        "dev": [
            "pytest>=7.0.0"
        ]
    },
    entry_points={
        "console_scripts": [
            "mustan-agent=main:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Environment :: Console",
    ],
)

