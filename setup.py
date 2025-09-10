from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pr-reviewer",
    version="0.1.0",
    author="PR Reviewer Contributors",
    author_email="",
    description="Multi-LLM Code Review Tool - AI-powered code reviews with intelligent navigation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pr-reviewer/pr-reviewer",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Quality Assurance",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "click>=8.0.0",
        "pyyaml>=6.0",
        "gitpython>=3.1.0",
        "google-generativeai>=0.3.0",
        "rich>=13.0.0",  # For nice terminal output
        "pathspec>=0.11.0",  # For gitignore parsing
        "aiohttp>=3.8.0",  # For async HTTP client
        "fastapi>=0.100.0",  # For review service
        "uvicorn>=0.22.0",  # For running service
        "python-dotenv>=1.0.0",  # For .env file support
        "requests>=2.28.0",  # For sync HTTP calls
    ],
    entry_points={
        "console_scripts": [
            "reviewer=reviewer.cli:main",
            "reviewer-mcp=reviewer.mcp_server:run",
        ],
    },
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.10.0",
            "aioresponses>=0.7.4",  # For mocking aiohttp
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "isort>=5.12.0",
            "pylint>=2.17.0",
            "ipython>=8.10.0",
            "pre-commit>=3.2.0",
        ],
        "mcp": [
            # MCP-specific dependencies if needed
        ],
    },
)