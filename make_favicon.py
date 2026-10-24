from pathlib import Path
from PIL import Image

src = Path("static/assets/images/logo.png")
out = Path("static/assets/images")
root = Path("root_files")
root.mkdir(exist_ok=True)

img = Image.open(src).convert("RGBA")
side = max(img.size)
canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
canvas.paste(img, ((side - img.width) // 2, (side - img.height) // 2))

canvas.resize((192, 192), Image.LANCZOS).save(out / "favicon-192.png")

apple = canvas.resize((180, 180), Image.LANCZOS)
bg = Image.new("RGB", (180, 180), "white")
bg.paste(apple, mask=apple.split()[3])
bg.save(out / "apple-touch-icon.png")

canvas.save(root / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
print("done")