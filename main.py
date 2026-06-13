import http.server
import socketserver

from http import HTTPStatus
from tomllib import load as tomlLoad

PORT = 8000

class SoundboardTomlException(Exception):
    pass

class SButtonMake:
    __slots__ = ('dataSrc', 'img')

    def __init__(self, dataSrc, img):
        self.dataSrc = f'data-src="{dataSrc}"' if dataSrc is not None else ""
        self.img = f'<img class="sound-btn-img" src="{img}">' if img is not None else ""

class SButton:
    __slots__ = ( 'dataSrc', 'img', 'make', 'onclick', 'svg', 'text', 'textColor')

    def __init__(self, i, dct):
        if not isinstance(dct, dict):
            raise SoundboardTomlException(f"button #{i} should be a table")
        self.dataSrc = dct.get('dataSrc')
        self.img = dct.get('img')
        if (onclick := dct.get('onclick')) is None:
            raise SoundboardTomlException(f"Missing value on button #{i}: onclick")
        self.onclick = onclick
        if (svg := dct.get('svg')) is None:
            raise SoundboardTomlException(f"Missing value on button #{i}: svg")
        self.svg = svg
        if (text := dct.get('text')) is None:
            raise SoundboardTomlException(f"Missing value on button #{i}: text")
        self.text = text
        if (textColor := dct.get('textColor')) is None:
            raise SoundboardTomlException(f"Missing value on button #{i}: textColor")
        self.textColor = textColor
        self.make = SButtonMake(self.dataSrc, self.img)

class SCSS:
    __slots__ = ( 'textColors')

    def __init__(self, dct):
        if not isinstance(dct, dict):
            raise SoundboardTomlException("css should be a table")
        if (textColors := dct.get('textColors')) is None:
            raise SoundboardTomlException(f"Missing value on css: textColors")
        self.textColors = textColors

class SCSSRoot:
    __slots__ = ( 'aliases', 'colors')

    def __init__(self, dct):
        if not isinstance(dct, dict):
            raise SoundboardTomlException("cssRoot should be a table")
        if (aliases := dct.get('aliases')) is None:
            raise SoundboardTomlException(f"Missing value on cssRoot: aliases")
        self.aliases = aliases
        if (colors := dct.get('colors')) is None:
            raise SoundboardTomlException(f"Missing value on cssRoot: colors")
        self.colors = colors

class SPage:
    __slots__ = ( 'btnSize', 'containerMaxWidth', 'fontFamily', 'heading1', 'title')

    def __init__(self, dct):
        if not isinstance(dct, dict):
            raise SoundboardTomlException("page should be a table")
        if (btnSize := dct.get('btnSize')) is None:
            raise SoundboardTomlException(f"Missing value on page: btnSize")
        self.btnSize = btnSize
        if (containerMaxWidth := dct.get('containerMaxWidth')) is None:
            raise SoundboardTomlException(f"Missing value on page: containerMaxWidth")
        self.containerMaxWidth = containerMaxWidth
        if (fontFamily := dct.get('fontFamily')) is None:
            raise SoundboardTomlException(f"Missing value on page: fontFamily")
        self.fontFamily = fontFamily
        if (heading1 := dct.get('heading1')) is None:
            raise SoundboardTomlException(f"Missing value on page: heading1")
        self.heading1 = heading1
        if (title := dct.get('title')) is None:
            raise SoundboardTomlException(f"Missing value on page: title")
        self.title = title

class SMakeCSS:
    __slots__ = ( 'textColors' )

    def __init__(self, textColors: dict[str, str]):
        if not isinstance(textColors, dict):
            raise SoundboardTomlException("css.textColors should be a table")
        self.textColors = ""
        for key, value in textColors.items():
            css_value = valueToCSSValue(value, errMsg = "All values in the css.textColors table should be strings")
            self.textColors += f"    .text-{key} {{ color: var(--{css_value}) }}\n"

class SMakeCSSRoot:
    __slots__ = ( 'aliases', 'colors' )

    def __init__(self, aliases: dict[str, str], colors: dict[str, str]):
        self._make_aliases(aliases)
        self._make_colors(colors)

    def _make_aliases(self, aliases: dict[str, str]):
        if not isinstance(aliases, dict):
            raise SoundboardTomlException("css.Root.aliases should be a table")
        self.aliases = ""
        for key, value in aliases.items():
            css_key = valueToCSSValue(key, errMsg = f"Invalid key: {key}")
            css_value = valueToCSSValue(value, errMsg = "All value in the cssRoot.aliases should be strings")
            self.aliases += f"      --{css_key}: var(--{css_value});\n"

    def _make_colors(self, colors: dict[str, str]):
        if not isinstance(colors, dict):
            raise SoundboardTomlException("css.Root.colors should be a table")
        self.colors = ""
        for key, value in colors.items():
            css_key = valueToCSSValue(key, errMsg = f"Invalid key: {key}")
            self.colors += f'      --{css_key}: "{value}";\n'

class SMake:
    __slots__ = ( 'buttons', 'css', 'cssRoot' )

    def __init__(self, buttons: [SButton], css: SCSS, cssRoot: SCSSRoot):
        self._make_buttons(buttons)
        self.css = SMakeCSS(css.textColors)
        self.cssRoot = SMakeCSSRoot(cssRoot.aliases, cssRoot.colors)

    def _make_buttons(self, buttons: [SButton]):
        self.buttons = ""
        for button in buttons:
            self.buttons += BUTTON_HTML.format(**slotsAsDict(button))

class SoundboardToml:
    __slots__ = ( 'buttons', 'css', 'cssRoot', 'make', 'page' )

    def __init__(self, dct):
        if not isinstance(dct, dict):
            raise SoundboardTomlException("No root table")
        buttons = buttons if (buttons := dct.get('buttons')) is not None else []
        self.buttons = [SButton(i, button) for i,button in enumerate(buttons)]
        if (css := dct.get('css')) is None:
            raise SoundboardTomlException("Missing value: css")
        self.css = SCSS(css)
        if (cssRoot := dct.get('cssRoot')) is None:
            raise SoundboardTomlException("Missing value: cssRoot")
        self.cssRoot = SCSSRoot(cssRoot)
        if (page := dct.get('page')) is None:
            raise SoundboardTomlException("Missing value: page")
        self.page = SPage(page)
        self.make = SMake(self.buttons, self.css, self.cssRoot)

def valueToCSSValue(value: str, *, errMsg: str) -> str:
    if not isinstance(value, str):
        raise SoundboardTomlException(errMsg)
    result = value[0].lower()
    for ch in value[1:]:
        if ch.isupper():
            result += '-'
        result += ch.lower()
    return result

def runServer():
    # prevents server being locked out of the port if the OS hasn't cleaned up
    # a previous instance of the server
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), http.server.SimpleHTTPRequestHandler) as httpd:
        print(f"Running server on port {PORT}...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Shutting down server...")

def readTomlFile(path: str) -> dict:
    '''Read data from toml file'''
    with open(path, 'rb') as file:
        return tomlLoad(file)

def slotsAsDict(objWithSlots: object) -> dict:
    return {attr: getattr(objWithSlots, attr) for attr in objWithSlots.__slots__}

def generateHtmlPage():
    # for now the toml and html files are hardcoded
    data = SoundboardToml(readTomlFile("index.toml"))
    indexHTML = PAGE_HTML.format(**slotsAsDict(data))
    with open("index.html", 'w') as file:
        file.write(indexHTML)

    print("Written index.html")

# {{{
BUTTON_HTML = """
        <div class="sound-item">
          <button class="sound-button-wrapper hand position-relative sound-btn hand p-0" {make.dataSrc} onclick="{onclick}">
            <svg class="sound-base-icon">
              <use class="sound-icon" xlink:href="{svg}"></use>
            </svg>
            {make.img}
          </button>
          <p class="sound-button-text text-{textColor}">{text}</p>
        </div>
""" # }}}
# {{{
PAGE_HTML = """
<!DOCTYPE HTML>
<head>
  <title>{page.title}</title>
  <style>
    :root {{
{make.cssRoot.colors}
{make.cssRoot.aliases}
      --btn-size: {page.btnSize};
      --container-max-width: {page.containerMaxWidth};
    }}

    html,
    body {{
      font-family: {page.fontFamily};
    }}

    .p-0 {{
      padding: 0
    }}

    .hand {{
      cursor: pointer
    }}

    .position-relative {{
      position: relative !important
    }}

    .container {{
      width: 100%;
      margin-right: auto;
      margin-left: auto;
      max-width: var(--container-max-width);
    }}

    main {{
      text-align: center;
      margin: 40px auto;
    }}

    .soundboard {{
      margin: 35px 0;
      padding: 10px 0;
      display: flex;
      flex-wrap: wrap;
      gap: 32px 32px;
      justify-content: center;
    }}

    .sound-item {{
      width: var(--btn-size);
      word-wrap: break-word;
    }}

    .sound-btn {{
      background-color: #fff0;
      border: none;
    }}

    .sound-btn:hover {{
      transform: scale(1.1);
    }}

    .sound-button-wrapper:active {{
      transform: scaleY(.8)
    }}

    .sound-button-wrapper svg {{
      height: var(--btn-size);
      width: var(--btn-size);
    }}

    .sound-btn-img {{
      position: absolute;
      top: 44%;
      left: 50%;
      transform: translate(-50%, -50%);
      width: 65%;
      height: 65%;
      object-fit: cover;
      border-radius: 50%;
      pointer-events: none;
      z-index: 2;
    }}

    .sound-button-text {{
      margin-top: 4px;
      word-break: break-word;
      min-height: 42px;
      overflow: hidden;
    }}

{make.css.textColors}
  </style>
</head>

<body>
  <main>
    <h1>{page.heading1}</h1>
    <div class="container">
      <div class="soundboard">
{make.buttons}
      </div>
    </div>
  </main>

  <svg style="display: none" xmlns="http://www.w3.org/2000/svg">
    <symbol id="btn-blue" viewBox="0 0 200 200">
      <circle cx="100" cy="100" r="90" fill="#444" stroke="#222" stroke-width="4"></circle> <circle cx="100" cy="90" r="80" fill="#42b6eb" stroke="black" stroke-width="4"></circle> <circle cx="100" cy="80" r="75" fill="lightskyblue" opacity="0.6"></circle> <defs> <filter id="glow"> <feGaussianBlur stdDeviation="8" result="coloredBlur"></feGaussianBlur> <feMerge> <feMergeNode in="coloredBlur"></feMergeNode> <feMergeNode in="SourceGraphic"></feMergeNode> </feMerge> </filter> </defs> <circle cx="100" cy="90" r="60" fill="#168dc2" opacity="0.3" filter="url(#glow)"></circle>
    </symbol>
    <symbol id="btn-dark-gray" viewBox="0 0 200 200">
      <circle cx="100" cy="100" r="90" fill="#444" stroke="#222" stroke-width="4"></circle> <circle cx="100" cy="90" r="80" fill="#555" stroke="black" stroke-width="4"></circle> <circle cx="100" cy="80" r="75" fill="#777" opacity="0.6"></circle> <defs> <filter id="glow"> <feGaussianBlur stdDeviation="8" result="coloredBlur"></feGaussianBlur> <feMerge> <feMergeNode in="coloredBlur"></feMergeNode> <feMergeNode in="SourceGraphic"></feMergeNode> </feMerge> </filter> </defs> <circle cx="100" cy="90" r="60" fill="#555" opacity="0.3" filter="url(#glow)"></circle>
    </symbol>
    <symbol id="btn-green" viewBox="0 0 200 200">
      <circle cx="100" cy="100" r="90" fill="#444" stroke="#222" stroke-width="4"></circle> <circle cx="100" cy="90" r="80" fill="green" stroke="black" stroke-width="4"></circle> <circle cx="100" cy="80" r="75" fill="limegreen" opacity="0.6"></circle> <defs> <filter id="glow"> <feGaussianBlur stdDeviation="8" result="coloredBlur"></feGaussianBlur> <feMerge> <feMergeNode in="coloredBlur"></feMergeNode> <feMergeNode in="SourceGraphic"></feMergeNode> </feMerge> </filter> </defs> <circle cx="100" cy="90" r="60" fill="green" opacity="0.3" filter="url(#glow)"></circle>
    </symbol>
    <symbol id="btn-indigo" viewBox="0 0 200 200">
      <circle cx="100" cy="100" r="90" fill="#444" stroke="#222" stroke-width="4"></circle> <circle cx="100" cy="90" r="80" fill="indigo" stroke="black" stroke-width="4"></circle> <circle cx="100" cy="80" r="75" fill="#ac7ccf" opacity="0.6"></circle> <defs> <filter id="glow"> <feGaussianBlur stdDeviation="8" result="coloredBlur"></feGaussianBlur> <feMerge> <feMergeNode in="coloredBlur"></feMergeNode> <feMergeNode in="SourceGraphic"></feMergeNode> </feMerge> </filter> </defs> <circle cx="100" cy="90" r="60" fill="indigo" opacity="0.3" filter="url(#glow)"></circle>
    </symbol>
    <symbol id="btn-light-gray" viewBox="0 0 200 200">
      <circle cx="100" cy="100" r="90" fill="#666" stroke="#444" stroke-width="4"></circle> <circle cx="100" cy="90" r="80" fill="#D3D3D3" stroke="black" stroke-width="4"></circle> <circle cx="100" cy="80" r="75" fill="#F0F0F0" opacity="0.6"></circle> <defs> <filter id="glow"> <feGaussianBlur stdDeviation="8" result="coloredBlur"></feGaussianBlur> <feMerge> <feMergeNode in="coloredBlur"></feMergeNode> <feMergeNode in="SourceGraphic"></feMergeNode> </feMerge> </filter> </defs> <circle cx="100" cy="90" r="60" fill="#999999" opacity="0.3" filter="url(#glow)"></circle>
    </symbol>
    <symbol id="btn-orange" viewBox="0 0 200 200">
      <circle cx="100" cy="100" r="90" fill="#444" stroke="#222" stroke-width="4"></circle> <circle cx="100" cy="90" r="80" fill="#ee812b" stroke="black" stroke-width="4"></circle> <circle cx="100" cy="80" r="75" fill="#f7a949" opacity="0.6"></circle> <defs> <filter id="glow"> <feGaussianBlur stdDeviation="8" result="coloredBlur"></feGaussianBlur> <feMerge> <feMergeNode in="coloredBlur"></feMergeNode> <feMergeNode in="SourceGraphic"></feMergeNode> </feMerge> </filter> </defs> <circle cx="100" cy="90" r="60" fill="#c74a0c" opacity="0.3" filter="url(#glow)"></circle>
    </symbol>
    <symbol id="btn-pink" viewBox="0 0 200 200">
      <circle cx="100" cy="100" r="90" fill="#444" stroke="#222" stroke-width="4"></circle> <circle cx="100" cy="90" r="80" fill="#f54ca7" stroke="black" stroke-width="4"></circle> <circle cx="100" cy="80" r="75" fill="#ff87c8" opacity="0.6"></circle> <defs> <filter id="glow"> <feGaussianBlur stdDeviation="8" result="coloredBlur"></feGaussianBlur> <feMerge> <feMergeNode in="coloredBlur"></feMergeNode> <feMergeNode in="SourceGraphic"></feMergeNode> </feMerge> </filter> </defs> <circle cx="100" cy="90" r="60" fill="#e43995" opacity="0.3" filter="url(#glow)"></circle>
    </symbol>
    <symbol id="btn-red" viewBox="0 0 200 200">
      <circle cx="100" cy="100" r="90" fill="#666" stroke="#222" stroke-width="4"></circle> <circle cx="100" cy="90" r="80" fill="#cc0505" stroke="black" stroke-width="4"></circle> <circle cx="100" cy="80" r="75" fill="#ff4545" opacity="0.6"></circle> <defs> <filter id="glow"> <feGaussianBlur stdDeviation="8" result="coloredBlur"></feGaussianBlur> <feMerge> <feMergeNode in="coloredBlur"></feMergeNode> <feMergeNode in="SourceGraphic"></feMergeNode> </feMerge> </filter> </defs> <circle cx="100" cy="90" r="60" fill="#a50000" opacity="0.3" filter="url(#glow)"></circle>
    </symbol>
    <symbol id="btn-yellow" viewBox="0 0 200 200">
      <circle cx="100" cy="100" r="90" fill="#666" stroke="#444" stroke-width="4"></circle> <circle cx="100" cy="90" r="80" fill="#f6c418" stroke="black" stroke-width="4"></circle> <circle cx="100" cy="80" r="75" fill="#fff46a" opacity="0.6"></circle> <defs> <filter id="glow"> <feGaussianBlur stdDeviation="8" result="coloredBlur"></feGaussianBlur> <feMerge> <feMergeNode in="coloredBlur"></feMergeNode> <feMergeNode in="SourceGraphic"></feMergeNode> </feMerge> </filter> </defs> <circle cx="100" cy="90" r="60" fill="#bfa615" opacity="0.3" filter="url(#glow)"></circle>
    </symbol>
  </svg>

  <script>
    let audioPlayer = new Audio;

    function togglePlay(e) {{
      const data_src = e.getAttribute("data-src")
      if (data_src) {{
        audioPlayer.src = data_src
        audioPlayer.play()
      }}
    }}

    function pause() {{
      audioPlayer.pause()
    }}
  </script>

</body>

""" # }}}

if __name__ == "__main__":
    generateHtmlPage()
    runServer()

# vim: foldmethod=marker
