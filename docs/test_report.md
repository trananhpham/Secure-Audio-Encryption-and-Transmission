# Test Report

All required tests passed with pytest.

Command:

```bash
pytest -q --basetemp=.pytest_tmp
```

Result:

```text
13 passed in 2.30s
```

Covered cases:

- Valid audio transfer.
- Missing segment detection.
- Tampered segment detection.
- Reordered segment detection.
- Wrong format mix rejection.
- Replay attack detection.
- Original and reconstructed file hash comparison.
- Web API smoke tests.
