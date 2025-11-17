# Testing Guide - Trading Alerts Authentication System

## 🚀 Quick Start

### Windows
```cmd
# Option 1: Batch file (recommended)
test_all.bat

# Option 2: Python directly
python test_all.py
```

### Linux/Mac
```bash
# Option 1: Make executable and run
chmod +x test_all.py
./test_all.py

# Option 2: Python directly
python3 test_all.py
```

## 📦 Prerequisites

Install required dependencies first:

```bash
# Install all dependencies
pip install -r requirements.txt

# Or install core testing dependencies only:
pip install PyJWT bcrypt boto3 pydantic
```

## 🧪 Test Suites

The `test_all.py` script runs 3 test suites:

### 1. Unit Tests (8 tests)
- **File:** `test_unit_auth.py`
- **Tests:**
  - Password hashing (SHA256)
  - JWT token generation (3-part structure)
  - JWT token validation
  - JWT tampering detection (security)
  - Session storage (save, retrieve, delete)
  - Multiple sessions per user
  - Full authentication flow

### 2. Production Features (7 tests)
- **File:** `test_production_features.py`
- **Tests:**
  - bcrypt library availability
  - bcrypt password hashing ($2b$12$ format)
  - bcrypt password verification
  - Rate limiting (normal usage)
  - Rate limiting (lockout after 5 attempts)
  - Rate limiting (auto-unlock after timeout)
  - Full login flow (requires AWS credentials)

### 3. Demo Script
- **File:** `demo_auth.py`
- **Tests:**
  - Interactive demonstration of authentication flow
  - Registration → Login → Validation → Logout

## 📊 Expected Results

```
================================================================================
                    TESTING AUTHENTICATION SYSTEM
================================================================================

✅ All dependencies installed
✅ All syntax checks passed
✅ Unit Tests: 8/8 passed
✅ Production Features: 6/7 passed (1 AWS test expected to fail in dev)
✅ Demo Script: passed

Overall: 2/3 test suites passed completely

Total Time: ~3-5 seconds
```

## ⚠️ Known Issues

### AWS Credentials Test
One test in Production Features suite will fail if AWS credentials are not configured:

```
❌ Test: Full login flow with DynamoDB
   Reason: botocore.exceptions.NoCredentialsError
   Solution: This is expected in dev environment. In production, configure AWS credentials.
```

This is **NORMAL** and doesn't affect the core functionality. All critical tests (bcrypt, rate limiting, JWT) will pass.

### Windows-Specific Issues

#### 1. Python not found
```cmd
C:\> python test_all.py
'python' is not recognized as an internal or external command
```

**Solution:**
- Install Python from https://www.python.org/downloads/
- During installation, check "Add Python to PATH"
- OR use `python3` instead of `python`

#### 2. Module not found
```cmd
ModuleNotFoundError: No module named 'jwt'
```

**Solution:**
```cmd
pip install -r requirements.txt
```

## 🔍 Running Individual Tests

You can run each test suite separately:

### Unit Tests Only
```bash
python test_unit_auth.py
```

### Production Features Only
```bash
python test_production_features.py
```

### Demo Only
```bash
python demo_auth.py
```

## 📝 Test Output

### Success Output
```
🔐 Testing Authentication System
================================

[1/8] Test: Password hashing
      ✅ Password hashing works correctly

[2/8] Test: JWT token generation
      ✅ JWT token structure is valid (3 parts)

...

================================================================================
✅ ALL TESTS PASSED
================================================================================
```

### Failure Output
```
[5/8] Test: JWT tampering detection
      ❌ FAILED: Token should be rejected
      Expected: False
      Got: True

================================================================================
⚠️ 1 TEST(S) FAILED
================================================================================
```

## 🛠️ Troubleshooting

### Test hangs on "Checking dependencies"
- **Cause:** Network issues downloading packages
- **Solution:** Run `pip install -r requirements.txt` first

### All tests fail with "No module named 'src'"
- **Cause:** Wrong working directory
- **Solution:** Run tests from repository root:
  ```bash
  cd /path/to/trading-alerts-system
  python test_all.py
  ```

### bcrypt tests fail on Windows
- **Cause:** bcrypt requires C++ Build Tools on Windows
- **Solution:**
  1. Install Visual Studio Build Tools: https://visualstudio.microsoft.com/downloads/
  2. OR install pre-built wheel: `pip install bcrypt --only-binary bcrypt`

## 📚 Further Reading

- **Authentication Docs:** `docs/AUTHENTICATION.md`
- **Production Enhancements:** `docs/PRODUCTION_ENHANCEMENTS.md`
- **Test Reports:** `TEST_REPORT.md`

## 💡 Tips

- Run tests before committing code changes
- Run tests after pulling updates
- Check test output for warnings even if tests pass
- If a test fails unexpectedly, check recent code changes

## 📞 Support

If tests fail unexpectedly:

1. Check this README for known issues
2. Review test output for specific error messages
3. Ensure all dependencies are installed
4. Try running individual test files to isolate the issue
5. Check docs/AUTHENTICATION.md for system requirements
