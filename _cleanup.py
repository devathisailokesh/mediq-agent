import shutil, pathlib
target = pathlib.Path(__file__).parent / "src" / "models"
if target.exists():
    shutil.rmtree(target)
    print(f"Deleted: {target}")
else:
    print("Already gone")
