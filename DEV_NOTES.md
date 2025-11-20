# Development Notes

## Python Command
- Use `py` instead of `python` or `python3` on this system
- Example: `py generate_assembly.py`

## Common Commands

### Generate Assembly
```bash
py generate_assembly.py
```

### Run Training
```bash
py run_training.py
py run_comprehensive_training.py
py run_production_training.py
```

### Git Operations
```bash
git add -A
git commit -m "message"
git push
git status
git log --oneline -5
```

### Check Fusion Logs
```bash
Get-Content c:/Users/jrdnh/Documents/ai-fusion/shared/fusion_logs.jsonl -Tail 20
```

### Clean Up Test Files
```bash
Remove-Item c:/Users/jrdnh/Documents/ai-fusion/shared/tasks/task_*.json
Remove-Item c:/Users/jrdnh/Documents/ai-fusion/shared/results/result_*.json
```

## File Management
- Avoid creating too many files
- Keep test tasks minimal
- Clean up old test files regularly
- Use `.gitignore` to exclude generated files
