

import requests

HCTI_API_ENDPOINT = "https://hcti.io/v1/image"
# Retrieve these from 
HCTI_API_USER_ID = '6028e147-6062-45a6-adc4-2c5593220521'
HCTI_API_KEY = '4fe8a261-acd4-49f7-a0e4-c121311d85b7'

# data = { 'html': "<div class='box'>Hello, world!</div>",
#          'css': ".box { color: white; background-color: #0f79b9; padding: 10px; font-family: Roboto }",
#           }


data = {"google_fonts": "Roboto"}

with open("../image/profile.html") as f:
    data["html"] = f.read()
with open("../image/profile.css") as f:
    data["css"] = f.read()


image = requests.post(url = HCTI_API_ENDPOINT, data = data, auth=(HCTI_API_USER_ID, HCTI_API_KEY))

print("Your image URL is: %s"%image.json()['url'])

quit()


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