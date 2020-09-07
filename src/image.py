from PIL import Image, ImageDraw, ImageFont

class Donk(dict):
    def __getattr__(self, name):
        return self[name]

human = Donk(
    {
        "name" : "Clark#1062"
    }
)

human.name

class ImageBuilder:
    def __init__(self, background):
        # self.background = background
    
        background = Image.open("bg.png").convert("RGBA")

        txt = Image.new("RGBA", base.size, (255,255,255,0))
        self.base = ImageDraw.Draw(txt)

    def add_image(self, url):
        pass

    def render(self):
        pass

# get an image
background = Image.open("bg.png").convert("RGBA")

# make a blank image for the text, initialized to transparent text color
txt = Image.new("RGBA", background.size, (255,255,255,0))

base = ImageDraw.Draw(txt)
font = ImageFont.truetype("RetroVille.ttf", 40)

# draw text, half opacity
base.text((10,10), "Hello", font=font, fill=(255,255,255,128))
# draw text, full opacity
base.text((10,60), "World", font=font, fill=(255,255,255,255))

out = Image.alpha_composite(background, txt)

out.show()
quit()