from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

options = webdriver.ChromeOptions()

options.add_experimental_option(name = "detach", value = True)

driver = webdriver.Chrome(options=options, service=ChromeService(ChromeDriverManager().install()))

website = 'https://www.adamchoi.co.uk/overs/detailed'
path = '/Users/yasir_savanur/Downloads/chromedriver-mac-arm64/chromedriver'
s = ChromeService(path)

driver.get(website)

wait = WebDriverWait(driver, 10)

# 1. Consent cookies
consent_button = wait.until(
    EC.presence_of_element_located(
        (By.XPATH, "//p[text()='Consent']")
    )
)

driver.execute_script("arguments[0].click();", consent_button)

# 2. All matches
all_matches_button = wait.until(
    EC.presence_of_element_located(
        (By.XPATH, "//label[@analytics-event='All matches']")
    )
)    
driver.execute_script("arguments[0].click();", all_matches_button)

# driver.quit()