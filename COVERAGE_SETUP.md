# Test Coverage Setup Guide

## Overview
This project has comprehensive test coverage reporting integrated with GitHub Actions and Codecov.

## Current Status
- ✅ **749 tests passing** (100% pass rate)
- ✅ Coverage reporting enabled
- ✅ GitHub Actions integration configured
- ✅ Codecov integration ready

---

## Features

### 1. **Automated Coverage Reports**
- ✅ Generated on every push and pull request
- ✅ Separate reports for Python 3.11 and 3.12
- ✅ Combined unit + integration test coverage
- ✅ HTML reports downloadable as artifacts

### 2. **Pull Request Comments**
- ✅ Automatic coverage comments on PRs
- ✅ Shows coverage changes
- ✅ Color-coded thresholds:
  - 🟢 Green: ≥ 80%
  - 🟠 Orange: 70-79%
  - 🔴 Red: < 70%

### 3. **Multiple Report Formats**
- **XML**: For Codecov upload
- **Terminal**: In CI logs
- **HTML**: Downloadable artifacts
- **Coverage summary**: Shows missing lines

---

## Setup Instructions

### 1. Configure Codecov Token

Add your Codecov token to GitHub repository secrets:

1. Go to [codecov.io](https://codecov.io)
2. Sign in with GitHub
3. Add your repository
4. Copy the upload token
5. Go to your GitHub repo → Settings → Secrets → Actions
6. Add new secret:
   - Name: `CODECOV_TOKEN`
   - Value: Your Codecov upload token

### 2. Enable Workflow

The coverage workflow is already configured in `.github/workflows/api-tests.yml` and runs automatically on:
- Pull requests
- Pushes to main branch
- Manual workflow dispatch

---

## Local Coverage Testing

### Generate Coverage Report Locally

```bash
cd api

# Run all tests with coverage
pytest --cov=src --cov-report=html --cov-report=term

# Run only unit tests with coverage
pytest tests/unit/ --cov=src --cov-report=html

# Run with detailed missing lines
pytest --cov=src --cov-report=term-missing
```

### View HTML Report

```bash
# After running tests with --cov-report=html
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Coverage Configuration

Coverage settings are in `api/.coveragerc` or `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/migrations/*",
    "*/__pycache__/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

---

## GitHub Actions Workflow

### What Happens on Each Run

1. **Setup Environment**
   - Checkout code
   - Setup Python (3.11 & 3.12)
   - Install dependencies with `uv`
   - Start PostgreSQL & Redis services

2. **Run Tests**
   - Unit tests with coverage
   - Integration tests with appended coverage
   - Generate coverage reports (XML, HTML, Terminal)

3. **Upload Reports**
   - Upload to Codecov (with token)
   - Upload HTML report as GitHub artifact
   - Comment on PR with coverage summary

4. **Artifacts Available**
   - Coverage HTML reports (30 days retention)
   - Download from Actions → Workflow run → Artifacts

---

## Coverage Badges

### Add Badge to README

Once Codecov is set up, add this badge:

```markdown
[![codecov](https://codecov.io/gh/YOUR_USERNAME/synkora/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_USERNAME/synkora)
```

Replace `YOUR_USERNAME` with your GitHub username.

---

## Coverage Thresholds

### Current Configuration

- **Minimum Green**: 80% coverage
- **Minimum Orange**: 70% coverage
- **Below 70%**: Red (needs improvement)

### Adjust Thresholds

Edit `.github/workflows/api-tests.yml`:

```yaml
- name: Comment coverage on PR
  uses: py-cov-action/python-coverage-comment-action@v3
  with:
    MINIMUM_GREEN: 85    # Change this
    MINIMUM_ORANGE: 75   # Change this
```

---

## Viewing Coverage Reports

### 1. In GitHub Actions

1. Go to Actions tab
2. Click on a workflow run
3. Scroll to "Upload coverage HTML report"
4. Download the artifact
5. Unzip and open `index.html`

### 2. On Codecov Dashboard

1. Visit: `https://codecov.io/gh/YOUR_USERNAME/synkora`
2. View detailed coverage reports
3. See coverage trends over time
4. Compare branches and PRs

### 3. In Pull Request Comments

Coverage bot automatically comments on PRs with:
- Overall coverage percentage
- Coverage change vs base branch
- List of files with coverage changes
- Links to detailed reports

---

## Troubleshooting

### Coverage Report Not Uploading

**Problem**: Codecov upload fails

**Solution**:
1. Check `CODECOV_TOKEN` secret is set correctly
2. Verify token hasn't expired on codecov.io
3. Check workflow logs for specific error

### No PR Comment

**Problem**: Coverage comment doesn't appear on PR

**Solution**:
1. Ensure workflow has `pull_request` trigger
2. Check GitHub token has required permissions
3. Verify `python-coverage-comment-action` step runs

### Low Coverage Warning

**Problem**: Coverage drops below threshold

**Solution**:
1. Check which files/lines aren't covered
2. Add tests for uncovered code
3. Run locally: `pytest --cov=src --cov-report=term-missing`
4. Focus on files shown with low coverage %

### HTML Report Not Generated

**Problem**: No htmlcov folder

**Solution**:
```bash
# Make sure to include --cov-report=html
pytest --cov=src --cov-report=html --cov-report=term
```

---

## Best Practices

### 1. **Write Tests First**
- Aim for > 80% coverage
- Focus on critical business logic
- Don't forget edge cases

### 2. **Review Coverage in PRs**
- Check coverage changes before merging
- Don't merge PRs that significantly reduce coverage
- Address low-coverage areas

### 3. **Exclude What Shouldn't Be Covered**
```python
# Use pragma: no cover for legitimate exclusions
def development_only_function():  # pragma: no cover
    pass
```

### 4. **Monitor Trends**
- Watch coverage trends on Codecov
- Set up alerts for coverage drops
- Celebrate coverage improvements! 🎉

---

## Advanced Features

### Coverage by Test Type

```bash
# Unit tests only
pytest tests/unit/ --cov=src --cov-report=term

# Integration tests only  
pytest tests/integration/ --cov=src --cov-report=term

# Combined (default in CI)
pytest --cov=src --cov-report=term
```

### Coverage for Specific Modules

```bash
# Coverage for specific package
pytest --cov=src/services --cov-report=term

# Coverage for specific file
pytest --cov=src/services/auth_service.py --cov-report=term
```

### Parallel Testing with Coverage

```bash
# Run tests in parallel and collect coverage
pytest -n auto --cov=src --cov-report=html
```

---

## Quick Reference

### Common Commands

```bash
# Full coverage report
pytest --cov=src --cov-report=html --cov-report=term

# Show missing lines
pytest --cov=src --cov-report=term-missing

# Fail if coverage below 80%
pytest --cov=src --cov-fail-under=80

# Generate only XML for CI
pytest --cov=src --cov-report=xml

# Colored output in CI
pytest --cov=src --cov-report=term --color=yes
```

### File Locations

- **Coverage config**: `api/pyproject.toml` or `api/.coveragerc`
- **HTML reports**: `api/htmlcov/`
- **XML reports**: `api/coverage.xml`
- **CI workflow**: `.github/workflows/api-tests.yml`

---

## Resources

- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Codecov Documentation](https://docs.codecov.com/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

---

## Summary

✅ **Coverage is now fully integrated!**

- Runs automatically on every PR/push
- Reports uploaded to Codecov
- PR comments show coverage changes
- HTML reports available as artifacts
- Easy to run locally

**Next Steps**:
1. Add `CODECOV_TOKEN` to GitHub secrets
2. Push changes to trigger workflow
3. View coverage reports on Codecov
4. Maintain > 80% coverage going forward

Happy testing! 🧪
