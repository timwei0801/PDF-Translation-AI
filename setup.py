from setuptools import setup, find_packages

setup(
    name="pdf-translator",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "anthropic>=0.21.0",
        "python-dotenv>=1.0.0",
        "PyMuPDF>=1.23.9",
        "pdfplumber>=0.10.3",
        "pytesseract>=0.3.10",
        "pillow>=10.2.0",
        "langdetect>=1.0.9",
        "sentence-transformers>=2.3.1",
        "scikit-learn>=1.4.0",
        "pandas>=2.2.0",
        "numpy>=1.26.3",
        "tqdm>=4.66.1",
        "python-pptx>=0.6.22"
    ],
    author="專案開發者",
    author_email="example@example.com",
    description="使用Claude API的專業PDF英譯中系統",
    keywords="pdf, translation, claude, ai",
    python_requires=">=3.8",
)