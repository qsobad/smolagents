from helium import get_driver
from smolagents import CodeAgent, HfApiModel, LiteLLMModel, tool, OpenAIServerModel
from smolagents.agents import ActionStep
from PIL import Image
import tempfile
import helium
from selenium import webdriver
from time import sleep
# model = HfApiModel("Qwen/Qwen2-VL-7B-Instruct")
# model = HfApiModel("https://lmqbs8965pj40e01.us-east-1.aws.endpoints.huggingface.cloud")

from dotenv import load_dotenv
load_dotenv()
import os


# model = OpenAIServerModel(
#     api_key=os.environ.get("TOGETHER_API_KEY"),
#     api_base="https://api.together.xyz/v1",
#     model_id="Qwen/Qwen2-VL-72B-Instruct"
# )

model = OpenAIServerModel(
    api_key=os.environ.get("OPENAI_API_KEY"),
    # api_base="https://api.together.xyz/v1",
    model_id="gpt-4o"
)



from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementNotInteractableException

def save_screenshot(step_log: ActionStep, agent: CodeAgent) -> None:
    sleep(1.0) # Let possible js animations happen
    driver = get_driver()
    current_step = step_log.step_number
    if driver is not None:
        for step_logs in agent.logs: # Remove previous screenshots from logs since they'll be replaced now
            if isinstance(step_log, ActionStep) and step_log.step_number <= current_step - 2:
                step_logs.observations_images = None
        with tempfile.NamedTemporaryFile(suffix='.png', delete=True) as tmp:
            driver.save_screenshot(tmp.name)
            with Image.open(tmp.name) as img:
                width, height = img.size
                print(f"Captured a browser screenshot: {width}x{height} pixels")
                step_log.observations_images = [img.copy()]  # Create a copy to ensure it persists, important!

    # Update observations with URL
    url_info = f"Current url: {driver.current_url}"
    if step_log.observations is None:
        step_log.observations = url_info
    else:
        step_log.observations += "\n" + url_info
    return


# Initialize driver and agent
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--force-device-scale-factor=1')
chrome_options.add_argument('--window-size=900,1200')
driver = helium.start_chrome("google.com", headless=False, options=chrome_options)

@tool
def close_popups() -> str:
    """
    Closes any visible modal or pop-up on the page. Use this to dismiss pop-up windows! This does not work on cookie consent banners.
    """
    # Common selectors for modal close buttons and overlay elements
    modal_selectors = [
        # Close buttons
        "button[class*='close']",
        "[class*='modal']",
        "[class*='modal'] button",
        "[class*='CloseButton']",
        "[aria-label*='close']",
        ".modal-close",
        ".close-modal",
        ".modal .close",
        # Overlay backgrounds
        ".modal-backdrop",
        ".modal-overlay",
        "[class*='overlay']"
    ]
    
    wait = WebDriverWait(driver, timeout=0.5)
    
    for selector in modal_selectors:
        try:
            # Check if any matching elements are visible
            elements = wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
            )
            
            for element in elements:
                if element.is_displayed():
                    try:
                        # Try clicking with JavaScript as it's more reliable
                        driver.execute_script("arguments[0].click();", element)
                    except ElementNotInteractableException:
                        # If JavaScript click fails, try regular click
                        element.click()
                    
        except TimeoutException:
            continue
        except Exception as e:
            print(f"Error handling selector {selector}: {str(e)}")
            continue
    return "Modals closed"

agent = CodeAgent(
    tools=[close_popups],
    model=model,
    additional_authorized_imports=["helium"],
    step_callbacks = [save_screenshot],
    max_steps=20,
    verbosity_level=2
)
# Run agent
helium_instructions = """
You can use helium to access websites. Don't bother about the helium driver, it's already managed.
First you need to import everything from helium, then you can do other actions!
Code:
```py
from helium import *
go_to('github.com')
click('Trending')   
```<end_code>
If you try to interact with an element and it's not found, you'll get a LookupError.
In general stop your action after each button click to see what happens on your screenshot.
Code:
```py
write('username', into='Username')
write('password', into='Password')
click('Sign in')
```<end_code>
To scroll up or down, use scroll_down or scrol_up with as an argument the number of pixels in the page (if larger than the page height, this will scroll to the bottom):
Code:
```py
import time
scroll_down(num_pixels=100000) # This will probably scroll all the way down
time.sleep(0.5)
```<end_code>
When you have pop-ups that have a cross icon to close, don't try to click the close icon by finding its element or targeting an 'X' element, just use your built-in tool to close them:
Code:
```py
close_popups()
time.sleep(0.5)
```<end_code>
Proceed in several steps rather than trying to do it all in one shot.
And at the end, only when you have your answer, return your final answer.
Code:
```py
final_answer("YOUR_ANSWER_HERE")
```<end_code>
You can use .exists() to check for the existence of an element. For example:
Code:
```py
if Text('Accept cookies?').exists():
    click('I accept')
```<end_code>
Normally the page loads quickly, no need to wait for many seconds.
To find elements on page, DO NOT try code-based element searches like 'contributors = find_all(S("ol > li"))': just look at the latest screenshot you have and read it visually!
Of course you can act on buttons like a user would do when navigating.
After each code blob you write, you will be automatically provided with an updated screenshot of the browser and the current browser url. Don't kill the browser either.
Never try to login.
"""
agent.run("""
I want to know how hard I need to work to have a trending repo. Could you navigate to the current trending repos on GitHub, and from the top one, get me the number of commits of the top contributor?""" + helium_instructions)