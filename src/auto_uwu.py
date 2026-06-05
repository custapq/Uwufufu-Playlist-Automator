import getpass
import re
import time
import random
import urllib.parse
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


OUTPUT_FILE = "spotify_to_youtube.txt"
LOGIN_URL = "https://uwufufu.com/auth/login"
UWUFUFU_URL = "https://uwufufu.com"


USERNAME_SELECTOR = "input[name='email']"
PASSWORD_SELECTOR = "input[name='password']"
LOGIN_BUTTON_SELECTOR = "button[type='submit']"
CREATE_GAME_BUTTON_SELECTOR = "a[href='/create-game']"
TITLE_SELECTOR = "input#title"
DESCRIPTION_SELECTOR = "textarea#description"
CHOICES_BUTTON_SELECTOR = "button[type='submit'].bg-uwu-red.py-2.px-4"
CHOICES_XPATH = "//span[normalize-space()='Choices']"
VIDEO_ICON_SELECTOR = "svg.lucide-tv-minimal-play"
INPUT_ID = "youtubeUrl"
ADD_BUTTON_CSS = "button.bg-uwu-red[type='submit']"


def get_user_credentials():
    """Get all necessary credentials and IDs from the user"""
    print("\n=== Spotify Playlist ===")
    spotify_url = input("Enter your Spotify playlist URL: ")

    print("\n=== UwuFufu Credentials ===")
    uwu_username = input("Enter your UwuFufu email: ")
    uwu_password = getpass.getpass("Enter your UwuFufu password: ")

    print("\n=== UwuFufu Game Details ===")
    game_title = input("Enter your game title: ")
    game_description = input("Enter your game description: ")

    return {
        "spotify_url": spotify_url,
        "uwu_username": uwu_username,
        "uwu_password": uwu_password,
        "game_title": game_title,
        "game_description": game_description
    }


def get_spotify_playlist_tracks_without_api(playlist_url):
    """Get tracks from a Spotify playlist by scraping the web page using Selenium"""
    print("\nAccessing Spotify playlist...")


    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")



    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 30)

    try:

        driver.get(playlist_url)
        print("Waiting for page to load...")


        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='tracklist-row']")))


        time.sleep(3)



        track_count_patterns = [
            r"(\d+)\s+songs?",
            r"(\d+)\s+tracks?",
            r"(\d+)\s+songs?,\s+\d+\s+hr",
            r"(\d+)\s+songs?,\s+\d+\s+min"
        ]

        page_text = driver.find_element(By.TAG_NAME, "body").text
        expected_track_count = None

        for pattern in track_count_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                expected_track_count = int(match.group(1))
                print(f"Playlist contains {expected_track_count} tracks according to page info")
                break


        print("Scrolling to load all tracks...")
        track_elements = driver.find_elements(By.CSS_SELECTOR, "[data-testid='tracklist-row']")


        if expected_track_count:
            while len(track_elements) < expected_track_count:

                driver.execute_script(
                    "arguments[0].scrollIntoView();",
                    track_elements[-1]
                )
                time.sleep(1.5)


                track_elements = driver.find_elements(By.CSS_SELECTOR, "[data-testid='tracklist-row']")


                if len(track_elements) >= expected_track_count:
                    break


                if len(track_elements) > expected_track_count * 1.5:
                    print("Found more tracks than expected. Will limit to expected count.")
                    break
        else:

            last_track_count = 0
            current_track_count = len(track_elements)

            while current_track_count > last_track_count:
                last_track_count = current_track_count


                driver.execute_script(
                    "arguments[0].scrollIntoView();",
                    track_elements[-1]
                )
                time.sleep(1.5)

                track_elements = driver.find_elements(By.CSS_SELECTOR, "[data-testid='tracklist-row']")
                current_track_count = len(track_elements)


        if expected_track_count and len(track_elements) > expected_track_count:
            track_elements = track_elements[:expected_track_count]

        print(f"Found {len(track_elements)} tracks in the playlist!")


        tracks = []

        for i, element in enumerate(track_elements):
            try:

                track_data = driver.execute_script("""
                    const row = arguments[0];

                    // Get track name
                    const trackNameElement = row.querySelector("[data-testid='internal-track-link']");
                    let trackName = trackNameElement ? trackNameElement.textContent.trim() : "";

                    // Get artist name(s)
                    const artistElements = row.querySelectorAll("a[data-testid='artist-link']");
                    const artists = [];
                    for (const artist of artistElements) {
                        artists.push(artist.textContent.trim());
                    }

                    // If no artist elements found, try alternate method (for Spotify layout variations)
                    if (artists.length === 0) {
                        const artistsContainer = row.querySelector("span[data-testid='artists-container']");
                        if (artistsContainer) {
                            const artistText = artistsContainer.textContent.trim();
                            if (artistText) {
                                artists.push(artistText);
                            }
                        }
                    }

                    const artistNames = artists.join(", ");

                    return {
                        name: trackName,
                        artist: artistNames
                    };
                """, element)

                if track_data and track_data.get('name') and track_data.get('artist'):
                    tracks.append({
                        "name": track_data['name'],
                        "artist": track_data['artist'],
                        "search_query": f"{track_data['name']} {track_data['artist']}"
                    })
            except Exception as e:
                print(f"Error extracting track {i + 1}: {str(e)}")


        if len(tracks) < min(10, len(track_elements)):
            print("JavaScript extraction yielded too few results. Trying alternate method...")
            tracks = []

            for i, element in enumerate(track_elements):
                try:

                    track_name_element = element.find_element(By.CSS_SELECTOR, "[data-testid='internal-track-link']")
                    track_name = track_name_element.text.strip()


                    artist_name = ""
                    try:

                        artist_elements = element.find_elements(By.CSS_SELECTOR, "a[data-testid='artist-link']")
                        if artist_elements:
                            artists = [el.text.strip() for el in artist_elements]
                            artist_name = ", ".join(artists)
                        else:

                            artist_container = element.find_element(By.CSS_SELECTOR,
                                                                    "span[data-testid='artists-container']")
                            artist_name = artist_container.text.strip()
                    except:

                        cells = element.find_elements(By.CSS_SELECTOR, "div[role='gridcell']")
                        if len(cells) > 1:
                            artist_name = cells[1].text.strip()

                    if track_name and artist_name:
                        tracks.append({
                            "name": track_name,
                            "artist": artist_name,
                            "search_query": f"{track_name} {artist_name}"
                        })
                except Exception as e:
                    print(f"Error extracting track {i + 1}: {str(e)}")
                    continue

        if not tracks:
            print("Failed to extract any tracks using both methods.")

        return tracks

    except Exception as e:
        print(f"Error scraping Spotify playlist: {str(e)}")
        return []

    finally:
        driver.quit()


def search_youtube_without_api(query):
    """Search YouTube for a video matching the query using web scraping"""

    encoded_query = urllib.parse.quote(query)


    url = f"https://www.youtube.com/results?search_query={encoded_query}"


    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }


    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return None


    video_ids = re.findall(r"watch\?v=(\S{11})", response.text)

    if video_ids:

        unique_ids = []
        for vid in video_ids:
            if vid not in unique_ids:
                unique_ids.append(vid)


        if unique_ids:
            return f"https://www.youtube.com/watch?v={unique_ids[0]}"

    return None


def create_youtube_links_file(tracks):
    """Generate a file with YouTube links for each track"""
    print(f"\nSearching YouTube for {len(tracks)} tracks...")
    youtube_links = []

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for i, track in enumerate(tracks):
            print(f"[{i + 1}/{len(tracks)}] Finding '{track['name']}' by {track['artist']}...")

            try:
                youtube_link = search_youtube_without_api(track['search_query'])

                if youtube_link:
                    line = f"{track['name']} - {track['artist']}: {youtube_link}"
                    youtube_links.append({
                        "title": f"{track['name']} - {track['artist']}",
                        "url": youtube_link
                    })
                else:
                    line = f"{track['name']} - {track['artist']}: No video found"

                f.write(line + "\n")


                time.sleep(random.uniform(1.0, 2.5))

            except Exception as e:
                print(f"  Error processing this track: {str(e)}")
                f.write(f"{track['name']} - {track['artist']}: Error finding video\n")

    print(f"\nYouTube links saved to {OUTPUT_FILE}")
    return youtube_links


def create_and_automate_uwufufu(credentials, youtube_links):
    """Create a game and add YouTube videos to UwuFufu using Selenium"""
    uwu_username = credentials["uwu_username"]
    uwu_password = credentials["uwu_password"]
    game_title = credentials["game_title"]
    game_description = credentials["game_description"]

    print(f"\nLaunching browser to automate UwuFufu...")


    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 30)

    try:

        print("Logging into UwuFufu...")
        driver.get(LOGIN_URL)


        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, USERNAME_SELECTOR))).send_keys(uwu_username)
        time.sleep(0.3)
        driver.find_element(By.CSS_SELECTOR, PASSWORD_SELECTOR).send_keys(uwu_password)
        time.sleep(0.3)
        driver.find_element(By.CSS_SELECTOR, LOGIN_BUTTON_SELECTOR).click()


        wait.until(EC.url_contains(UWUFUFU_URL))
        print("✅ Successfully logged in.")
        time.sleep(2)


        print("Finding Create Game button...")


        create_game_clicked = False


        try:

            create_game_links = driver.find_elements(By.CSS_SELECTOR, CREATE_GAME_BUTTON_SELECTOR)
            for link in create_game_links:
                if link.is_displayed():
                    print("Found 'Create Game' link by selector")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                    time.sleep(0.8)
                    link.click()
                    create_game_clicked = True
                    break
        except Exception as e:
            print(f"Could not find 'Create Game' link by selector: {str(e)}")


        if not create_game_clicked:
            try:
                print("Looking for 'Create Game' text in links/buttons...")

                xpath = "//*[contains(text(), 'Create Game') or contains(text(), 'New Game') or contains(text(), 'create game') or contains(text(), 'new game')]"
                create_elements = driver.find_elements(By.XPATH, xpath)

                for element in create_elements:
                    if element.is_displayed():

                        clickable = element

                        for _ in range(3):
                            try:
                                tag_name = driver.execute_script("return arguments[0].tagName;", clickable).lower()
                                if tag_name in ['a', 'button', 'div']:
                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", clickable)
                                    time.sleep(1)
                                    driver.execute_script("arguments[0].click();", clickable)
                                    create_game_clicked = True
                                    print(f"Clicked on {tag_name} element containing 'Create Game' text")
                                    break
                                clickable = driver.execute_script("return arguments[0].parentNode;", clickable)
                            except:
                                break

                        if create_game_clicked:
                            break
            except Exception as e:
                print(f"Error finding 'Create Game' by text: {str(e)}")


        if not create_game_clicked:
            try:
                print("Using JavaScript to find and click 'Create Game'...")
                clicked = driver.execute_script("""
                    // Function to check if element is visible
                    function isVisible(elem) {
                        if (!elem) return false;
                        if (window.getComputedStyle(elem).display === 'none') return false;
                        if (window.getComputedStyle(elem).visibility === 'hidden') return false;
                        if (elem.offsetParent === null) return false;
                        return true;
                    }

                    // Try direct href approach
                    const createLinks = document.querySelectorAll('a[href="/create-game"]');
                    for (const link of createLinks) {
                        if (isVisible(link)) {
                            link.click();
                            return true;
                        }
                    }

                    // Try links with 'create-game' in href
                    const createGameLinks = document.querySelectorAll('a[href*="create-game"]');
                    for (const link of createGameLinks) {
                        if (isVisible(link)) {
                            link.click();
                            return true;
                        }
                    }

                    // Try any element with Create Game text
                    const createTexts = ["Create Game", "New Game", "create game", "new game"];
                    for (const text of createTexts) {
                        const elements = Array.from(document.querySelectorAll('a, button, div')).filter(
                            el => isVisible(el) && el.textContent.includes(text)
                        );

                        for (const el of elements) {
                            el.click();
                            return true;
                        }
                    }

                    // Try header menu items
                    const headerItems = document.querySelectorAll('header a, header button, nav a, nav button');
                    for (const item of headerItems) {
                        if (isVisible(item) && 
                           (item.textContent.toLowerCase().includes('create') || 
                            item.textContent.toLowerCase().includes('new'))) {
                            item.click();
                            return true;
                        }
                    }

                    // Try clicking any "+" button (often used for create actions)
                    const plusButtons = Array.from(document.querySelectorAll('button')).filter(
                        btn => isVisible(btn) && btn.textContent.includes('+')
                    );
                    for (const btn of plusButtons) {
                        btn.click();
                        return true;
                    }

                    return false;
                """)

                if clicked:
                    create_game_clicked = True
                    print("Successfully clicked 'Create Game' using JavaScript")
                else:
                    print("JavaScript approach couldn't find the 'Create Game' button")
            except Exception as e:
                print(f"JavaScript approach error: {str(e)}")


        if not create_game_clicked:
            print("Attempting to navigate directly to create-game page...")
            driver.get("https://uwufufu.com/create-game")
            time.sleep(1)
            create_game_clicked = True






        print("✅ Successfully accessed the Create Game page.")

        wait.until(lambda driver: "create-game" in driver.current_url)


        print("Waiting for form to load...")
        time.sleep(1)


        title_elements = driver.find_elements(By.CSS_SELECTOR, TITLE_SELECTOR)
        if title_elements and any(el.is_displayed() for el in title_elements):
            print("Found title input using original selector")
        else:
            print("Original title selector not found, trying alternatives...")

            alternative_title_selectors = [
                "input#title",
                "input[name='title']",
                "input[placeholder*='title' i]",
                "input[placeholder*='name' i]",
                "input.form-control",
                "input.input"
            ]

            for selector in alternative_title_selectors:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    if el.is_displayed():
                        print(f"Found title input using alternative selector: {selector}")
                        title_input = el
                        break
                if 'title_input' in locals():
                    break


        if 'title_input' not in locals():
            print("Using JavaScript to find any suitable title input...")
            title_input = driver.execute_script("""
                // Find any visible input that might be for title
                const inputs = document.querySelectorAll('input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"])');
                for (const input of inputs) {
                    if (input.offsetParent !== null) {  // Check if visible
                        const placeholder = (input.placeholder || '').toLowerCase();
                        const id = (input.id || '').toLowerCase();
                        const name = (input.name || '').toLowerCase();

                        if (placeholder.includes('title') || placeholder.includes('name') ||
                            id.includes('title') || id.includes('name') ||
                            name.includes('title') || name.includes('name') ||
                            input === document.querySelector('form input')) {
                            return input;
                        }
                    }
                }

                // Last resort - return first visible text input
                for (const input of inputs) {
                    if (input.offsetParent !== null) {
                        return input;
                    }
                }

                return null;
            """)


        if 'title_input' in locals() and title_input:
            print("📝 Filling in game title...")
            title_input.clear()
            time.sleep(0.2)
            title_input.send_keys(game_title)
            time.sleep(0.2)
        else:
            print("⚠️ Could not find title input field!")


        description_input = None
        description_selectors = [
            DESCRIPTION_SELECTOR,
            "textarea#description",
            "textarea[name='description']",
            "textarea[placeholder*='description' i]",
            "textarea"
        ]

        for selector in description_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                if el.is_displayed():
                    description_input = el
                    print(f"Found description input using selector: {selector}")
                    break
            if description_input:
                break


        if not description_input:
            print("Using JavaScript to find description textarea...")
            description_input = driver.execute_script("""
                // Find any visible textarea
                const textareas = document.querySelectorAll('textarea');
                for (const textarea of textareas) {
                    if (textarea.offsetParent !== null) {
                        return textarea;
                    }
                }
                return null;
            """)


        if description_input:
            print("📝 Filling in game description...")
            description_input.clear()
            time.sleep(0.2)
            description_input.send_keys(game_description)
            time.sleep(0.2)
        else:
            print("⚠️ Could not find description input field!")


        print("Looking for submit button to continue...")
        choices_button = None


        try:
            choices_buttons = driver.find_elements(By.CSS_SELECTOR, CHOICES_BUTTON_SELECTOR)
            for btn in choices_buttons:
                if btn.is_displayed():
                    choices_button = btn
                    print("Found submit button using original selector")
                    break
        except:
            pass


        if not choices_button:
            submit_button_selectors = [
                "button[type='submit']",
                "button.bg-uwu-red",
                "button.btn-primary",
                "button.btn-submit",
                "input[type='submit']",
                "button:contains('Next')",
                "button:contains('Continue')",
                "button:contains('Create')",
                "button:contains('Submit')"
            ]

            for selector in submit_button_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for el in elements:
                        if el.is_displayed():
                            choices_button = el
                            print(f"Found submit button using alternative selector: {selector}")
                            break
                    if choices_button:
                        break
                except:
                    continue


        if not choices_button:
            print("Using JavaScript to find submit button...")
            choices_button = driver.execute_script("""
                // Find submit buttons
                const submitButtons = document.querySelectorAll('button[type="submit"]');
                for (const btn of submitButtons) {
                    if (btn.offsetParent !== null) {
                        return btn;
                    }
                }

                // Try buttons with certain text
                const buttonTexts = ['Next', 'Continue', 'Create', 'Submit', 'Save'];
                for (const text of buttonTexts) {
                    const buttons = Array.from(document.querySelectorAll('button')).filter(
                        btn => btn.offsetParent !== null && btn.textContent.includes(text)
                    );
                    if (buttons.length > 0) {
                        return buttons[0];
                    }
                }

                // Last resort - any visible button in a form
                const formButtons = Array.from(document.querySelectorAll('form button')).filter(
                    btn => btn.offsetParent !== null
                );
                if (formButtons.length > 0) {
                    return formButtons[0];
                }

                return null;
            """)


        if choices_button:
            print("Clicking submit button to continue...")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", choices_button)
            time.sleep(0.5)
            try:
                choices_button.click()
                print("✅ Submitted game details and moved to next step.")
            except Exception as e:
                print(f"Error clicking submit button: {str(e)}")
                print("Trying JavaScript click...")
                driver.execute_script("arguments[0].click();", choices_button)
        else:
            print("⚠️ Could not find a submit button! Manual intervention may be required.")


        time.sleep(3)



        current_url = driver.current_url
        if not re.search(r"/create-game/\d+", current_url):
            raise Exception(f"Unexpected URL after creating game: {current_url}")


        print("Looking for 'Choices' panel...")
        try:

            choices_element = wait.until(
                EC.element_to_be_clickable((By.XPATH, CHOICES_XPATH))
            )
            time.sleep(0.3)
            choices_element.click()
        except:
            print("Choices panel might already be open or using a different selector.")


        print("▶️ Proceeding to add videos.")
        time.sleep(2)


        video_button_clicked = False


        try:
            print("Looking for video input option...")


            video_icons = driver.find_elements(By.CSS_SELECTOR, VIDEO_ICON_SELECTOR)
            for icon in video_icons:
                if icon.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", icon)
                    time.sleep(0.3)
                    try:
                        icon.click()
                        video_button_clicked = True
                        print("Clicked video icon")
                        break
                    except:
                        pass


            if not video_button_clicked:
                video_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Video')]")
                for element in video_elements:
                    if element.is_displayed():
                        try:

                            clickable = element

                            for _ in range(3):
                                try:
                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", clickable)
                                    time.sleep(0.5)
                                    driver.execute_script("arguments[0].click();", clickable)
                                    video_button_clicked = True
                                    print("Clicked element with 'Video' text")
                                    break
                                except:
                                    clickable = driver.execute_script("return arguments[0].parentNode;", clickable)

                            if video_button_clicked:
                                break
                        except:
                            pass


            if not video_button_clicked:
                clicked = driver.execute_script("""
                    // Function to check if element is visible
                    function isVisible(elem) {
                        if (!elem) return false;
                        if (window.getComputedStyle(elem).display === 'none') return false;
                        if (window.getComputedStyle(elem).visibility === 'hidden') return false;
                        if (elem.offsetParent === null) return false;
                        return true;
                    }

                    // Try SVG icons first
                    const videoIcons = document.querySelectorAll('svg.lucide-tv-minimal-play, svg.lucide-video');
                    for (const icon of videoIcons) {
                        if (isVisible(icon)) {
                            // Try clicking the icon or its parent
                            try {
                                icon.click();
                                return true;
                            } catch(e) {
                                try {
                                    icon.parentNode.click();
                                    return true;
                                } catch(e2) {}
                            }
                        }
                    }

                    // Try any element containing "Video" text
                    const videoTexts = document.evaluate(
                        "//*[contains(text(), 'Video')]", 
                        document, 
                        null, 
                        XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, 
                        null
                    );

                    for (let i = 0; i < videoTexts.snapshotLength; i++) {
                        const element = videoTexts.snapshotItem(i);
                        if (isVisible(element)) {
                            try {
                                element.click();
                                return true;
                            } catch(e) {
                                // Try parent(s)
                                let parent = element.parentNode;
                                for (let j = 0; j < 3 && parent; j++) {
                                    try {
                                        parent.click();
                                        return true;
                                    } catch(e2) {
                                        parent = parent.parentNode;
                                    }
                                }
                            }
                        }
                    }

                    // Try any button that might be related to adding content
                    const contentButtons = document.querySelectorAll('button, div[role="button"]');
                    for (const btn of contentButtons) {
                        if (isVisible(btn) && 
                            (btn.textContent.includes('+') || 
                             btn.textContent.toLowerCase().includes('add') ||
                             btn.textContent.toLowerCase().includes('video'))) {
                            btn.click();
                            return true;
                        }
                    }

                    return false;
                """)

                if clicked:
                    video_button_clicked = True
                    print("Clicked video option using JavaScript")

        except Exception as e:
            print(f"Error finding video input option: {str(e)}")

        if not video_button_clicked:
            print("Warning: Could not confirm video input was revealed. Will attempt to continue.")
        else:
            print("▶️ Video input should now be revealed.")

        time.sleep(2)


        inp = None
        try:
            print("Looking for YouTube URL input field...")
            inp = wait.until(EC.presence_of_element_located((By.ID, INPUT_ID)))
            print("✅ Found YouTube URL input field.")
        except:
            print("Could not find input field by ID. Trying alternate methods...")


            input_elements = driver.find_elements(By.TAG_NAME, "input")
            for input_el in input_elements:
                if input_el.is_displayed():
                    placeholder = input_el.get_attribute("placeholder") or ""
                    if "youtube" in placeholder.lower() or "url" in placeholder.lower() or "video" in placeholder.lower():
                        inp = input_el
                        print("Found input field by placeholder text")
                        break


            if not inp:
                inp = driver.execute_script("""
                    // Find any visible input
                    const inputs = document.querySelectorAll('input:not([type="hidden"])');
                    for (const input of inputs) {
                        if (input.offsetParent !== null) {  // Check if visible
                            const placeholder = input.placeholder || '';
                            const id = input.id || '';
                            const name = input.name || '';

                            if (placeholder.toLowerCase().includes('youtube') || 
                                placeholder.toLowerCase().includes('url') ||
                                placeholder.toLowerCase().includes('video') ||
                                id.toLowerCase().includes('youtube') ||
                                id.toLowerCase().includes('url') ||
                                id.toLowerCase().includes('video') ||
                                name.toLowerCase().includes('youtube') ||
                                name.toLowerCase().includes('url') ||
                                name.toLowerCase().includes('video')) {
                                return input;
                            }
                        }
                    }

                    // Last resort - return first visible input
                    for (const input of inputs) {
                        if (input.offsetParent !== null) {
                            return input;
                        }
                    }

                    return null;
                """)

                if inp:
                    print("Found input field using JavaScript")

        if not inp:
            raise Exception("Could not find YouTube URL input field after multiple attempts")


        print(f"\nAdding {len(youtube_links)} videos to UwuFufu...")
        success_count = 0

        for i, item in enumerate(youtube_links):
            url = item['url']
            title = item['title']
            print(f"[{i + 1}/{len(youtube_links)}] Adding: {title}")

            try:


                inp.clear()
                time.sleep(0.3)
                inp.send_keys(url)
                time.sleep(0.3)


                driver.execute_script("""
                                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                                """, inp)
                time.sleep(0.3)
                inp.send_keys(Keys.TAB)
                time.sleep(0.5)


                add_button_clicked = False


                add_buttons = driver.find_elements(By.CSS_SELECTOR, ADD_BUTTON_CSS)
                for button in add_buttons:
                    if button.is_displayed():
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                        time.sleep(0.3)
                        try:
                            button.click()
                            add_button_clicked = True
                            success_count += 1
                            print("  Added video using primary button selector")
                            break
                        except:
                            pass


                if not add_button_clicked:
                    buttons = driver.find_elements(By.TAG_NAME, "button")
                    for button in buttons:
                        if button.is_displayed() and (
                                "add" in button.text.lower() or
                                "+" in button.text or
                                button.get_attribute("type") == "submit"
                        ):
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                            time.sleep(0.3)
                            try:
                                button.click()
                                add_button_clicked = True
                                success_count += 1
                                print("  Added video using button text search")
                                break
                            except:
                                pass


                if not add_button_clicked:
                    clicked = driver.execute_script("""
                                        // Function to check if element is visible
                                        function isVisible(elem) {
                                            if (!elem) return false;
                                            if (window.getComputedStyle(elem).display === 'none') return false;
                                            if (window.getComputedStyle(elem).visibility === 'hidden') return false;
                                            if (elem.offsetParent === null) return false;
                                            return true;
                                        }

                                        // First try the specific selector
                                        const addButtons = document.querySelectorAll("button.bg-uwu-red[type='submit']");
                                        for (const btn of addButtons) {
                                            if (isVisible(btn)) {
                                                btn.click();
                                                return true;
                                            }
                                        }

                                        // Try any submit button
                                        const submitButtons = document.querySelectorAll("button[type='submit']");
                                        for (const btn of submitButtons) {
                                            if (isVisible(btn)) {
                                                btn.click();
                                                return true;
                                            }
                                        }

                                        // Try buttons with text "Add" or "+"
                                        const allButtons = document.querySelectorAll('button');
                                        for (const btn of allButtons) {
                                            if (isVisible(btn) && 
                                               (btn.textContent.toLowerCase().includes('add') || 
                                                btn.textContent.includes('+'))) {
                                                btn.click();
                                                return true;
                                            }
                                        }

                                        // Try any button that seems to be in a form
                                        const formButtons = Array.from(document.querySelectorAll('button')).filter(
                                            btn => isVisible(btn) && btn.closest('form')
                                        );

                                        for (const btn of formButtons) {
                                            btn.click();
                                            return true;
                                        }

                                        return false;
                                    """)

                    if clicked:
                        add_button_clicked = True
                        success_count += 1
                        print("  Added video using JavaScript method")

                if not add_button_clicked:
                    print("  Failed to add this video - could not find or click Add button")


                time.sleep(0.5)

            except Exception as e:
                print(f"  Error adding this video: {str(e)}")

        print(f"\n🎉 Added {success_count} out of {len(youtube_links)} videos to UwuFufu!")
        print("Review and publish your game in the browser window.")


        input("\nPress Enter to close the browser and exit the program...")

    except Exception as e:
        print(f"\n❌ An error occurred during UwuFufu automation: {str(e)}")
        print("The browser will remain open for manual intervention.")
        input("Press Enter when you're ready to close the browser...")

    finally:
        driver.quit()


def main():
    print("=" * 50)
    print("🎵 Spotify to UwuFufu Automation Tool 🎮")
    print("=" * 50)
    print("\nThis tool will:")
    print("1. Get tracks from your Spotify playlist")
    print("2. Find corresponding YouTube videos")
    print("3. Create a new UwuFufu game")
    print("4. Add those videos to your UwuFufu game")


    credentials = get_user_credentials()

    try:

        tracks = get_spotify_playlist_tracks_without_api(credentials["spotify_url"])

        if not tracks:
            print("\n❌ Could not extract tracks from the Spotify playlist.")
            return

        print(f"\nSuccessfully extracted {len(tracks)} tracks!")


        youtube_links = create_youtube_links_file(tracks)


        valid_links = [item for item in youtube_links if item["url"] is not None]

        if not valid_links:
            print("\n❌ No valid YouTube links were found. Unable to continue.")
            return

        print(f"\nFound {len(valid_links)} valid YouTube links out of {len(tracks)} tracks.")


        proceed = input("\nReady to proceed with UwuFufu automation? (y/n): ").lower()
        if proceed != 'y':
            print("Automation cancelled. You can still use the YouTube links in the output file.")
            return


        create_and_automate_uwufufu(credentials, valid_links)

    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")


if __name__ == "__main__":
    main()