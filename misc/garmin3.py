from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

#setting up driver and loading page
driver = webdriver.Chrome()
driver.get("https://connect.garmin.com/signin/") #loading page
wait = WebDriverWait(driver, 20) #defining webdriver wait

#defining username and password, dont remove \n
username = 'daniel-garminconnect@pelleg.org'
password = 'xxx\n' #\n will act as an enter key and automatically login after having entered the password without clicking on confirm

#locating the login script under a function to make things more "visible"
def login():
    wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, "//iframe[@id='gauth-widget-frame-gauth-widget']"))) #switching frame
    wait.until(EC.visibility_of_element_located((By.ID, 'username'))).send_keys(username) #userame/email
    wait.until(EC.visibility_of_element_located((By.ID, 'password'))).send_keys(password) #password

#calling the login function and printing "you're in!!" when logged in
login()
print("you're in!!")
print('Url: ', driver.current_url)
