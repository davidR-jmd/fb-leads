"""LinkedIn browser automation service using Playwright (Single Responsibility)."""

import asyncio
import random
import logging
import threading
from typing import Any

from app.linkedin.interfaces import ILinkedInBrowser
from app.linkedin.schemas import LinkedInContact, LinkedInStatus

logger = logging.getLogger(__name__)


class LinkedInBrowser(ILinkedInBrowser):
    """Playwright-based LinkedIn browser automation (Thread-safe Singleton)."""

    # Singleton instance and lock
    _instance: "LinkedInBrowser | None" = None
    _lock: threading.Lock = threading.Lock()
    _initialized: bool = False

    # Browser settings for anti-detection
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
    VIEWPORT = {"width": 1920, "height": 1080}
    LOCALE = "fr-FR"
    TIMEZONE = "Europe/Paris"

    # LinkedIn URLs
    LOGIN_URL = "https://www.linkedin.com/login"
    FEED_URL = "https://www.linkedin.com/feed/"
    SEARCH_URL = "https://www.linkedin.com/search/results/people/"

    def __new__(cls, profile_path: str | None = None, headless: bool = True) -> "LinkedInBrowser":
        """Thread-safe singleton pattern with double-check locking."""
        if cls._instance is None:
            with cls._lock:
                # Double-check locking to prevent race conditions
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, profile_path: str | None = None, headless: bool = True) -> None:
        """Initialize browser with profile path for persistence (only once)."""
        # Prevent re-initialization
        if LinkedInBrowser._initialized:
            return

        with LinkedInBrowser._lock:
            if LinkedInBrowser._initialized:
                return

            self._profile_path = profile_path or "./browser-profiles/linkedin"
            self._headless = headless
            self._current_headless = headless  # Track current headless state
            self._context = None
            self._page = None
            self._busy = False
            LinkedInBrowser._initialized = True

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing purposes)."""
        with cls._lock:
            cls._instance = None
            cls._initialized = False

    def is_running(self) -> bool:
        """Check if browser is running."""
        return self._context is not None and self._page is not None

    def is_busy(self) -> bool:
        """Check if browser is busy with an operation."""
        return self._busy

    def set_busy(self, busy: bool) -> None:
        """Set busy state."""
        self._busy = busy

    async def launch(self, headless: bool | None = None) -> None:
        """Launch browser with persistent profile and stealth settings.

        Args:
            headless: Override the default headless setting. If None, uses instance default.
        """
        use_headless = headless if headless is not None else self._headless

        if self.is_running():
            # If already running but we need a different headless mode, restart
            if use_headless != self._current_headless:
                logger.info(f"Restarting browser: headless {self._current_headless} -> {use_headless}")
                await self.close()
            else:
                logger.info("Browser already running with correct headless mode")
                return

        try:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._current_headless = use_headless

            # Launch with persistent context for session persistence
            logger.info(f"Launching browser (headless={use_headless}, profile={self._profile_path})")
            self._context = await self._playwright.chromium.launch_persistent_context(
                self._profile_path,
                headless=use_headless,
                viewport=self.VIEWPORT,
                user_agent=self.USER_AGENT,
                locale=self.LOCALE,
                timezone_id=self.TIMEZONE,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                ],
            )

            # Get or create page
            if self._context.pages:
                self._page = self._context.pages[0]
            else:
                self._page = await self._context.new_page()

            logger.info("LinkedIn browser launched successfully")

        except Exception as e:
            logger.error(f"Failed to launch browser: {e}")
            await self.close()
            raise

    async def close(self) -> None:
        """Close browser and cleanup."""
        logger.info("Closing browser...")
        try:
            if self._context:
                try:
                    await self._context.close()
                except Exception as e:
                    logger.warning(f"Error closing context: {e}")
            if hasattr(self, "_playwright") and self._playwright:
                try:
                    await self._playwright.stop()
                except Exception as e:
                    logger.warning(f"Error stopping playwright: {e}")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
        finally:
            self._context = None
            self._page = None
            self._playwright = None
            self._busy = False
            self._current_headless = None  # Reset so next launch works
            logger.info("Browser closed")

    async def login(self, email: str, password: str) -> LinkedInStatus:
        """Attempt to login to LinkedIn."""
        if not self.is_running():
            await self.launch()

        try:
            self.set_busy(True)

            # Navigate to login page
            await self._page.goto(self.LOGIN_URL)
            await self._human_delay()

            # Fill credentials with human-like typing
            username_field = await self._page.query_selector("#username")
            if username_field:
                await self._human_type(username_field, email)
            else:
                await self._page.fill("#username", email)
            await self._human_delay(800, 1500)

            password_field = await self._page.query_selector("#password")
            if password_field:
                await self._human_type(password_field, password)
            else:
                await self._page.fill("#password", password)
            await self._human_delay(500, 1000)

            # Move mouse to button before clicking (human behavior)
            submit_button = await self._page.query_selector('button[type="submit"]')
            if submit_button:
                box = await submit_button.bounding_box()
                if box:
                    await self._human_mouse_move(
                        int(box["x"] + box["width"] / 2),
                        int(box["y"] + box["height"] / 2)
                    )
                    await asyncio.sleep(random.uniform(0.1, 0.3))

            # Click login button
            await self._page.click('button[type="submit"]')

            # Wait for navigation
            await self._page.wait_for_load_state("networkidle", timeout=15000)
            await self._human_delay()

            # Detect result based on URL
            current_url = self._page.url

            if self._is_feed_url(current_url):
                logger.info("LinkedIn login successful")
                return LinkedInStatus.CONNECTED

            if self._is_challenge_url(current_url):
                # Check if it's email verification
                if await self._is_email_verification_page():
                    logger.info("Email verification required")
                    return LinkedInStatus.NEED_EMAIL_CODE
                else:
                    logger.info("Manual login required (captcha or other)")
                    return LinkedInStatus.NEED_MANUAL_LOGIN

            if self._is_login_url(current_url):
                # Still on login page = wrong credentials
                logger.warning("Login failed - invalid credentials")
                return LinkedInStatus.ERROR

            logger.warning(f"Unknown state after login: {current_url}")
            return LinkedInStatus.ERROR

        except Exception as e:
            logger.error(f"Login error: {e}")
            return LinkedInStatus.ERROR

        finally:
            self.set_busy(False)

    async def inject_cookie(self, li_at_cookie: str) -> bool:
        """Inject li_at session cookie into browser.

        Args:
            li_at_cookie: The li_at cookie value from LinkedIn session.

        Returns:
            True if cookie was set successfully.
        """
        if not self.is_running():
            await self.launch()

        try:
            self.set_busy(True)

            # First navigate to LinkedIn to establish the domain context
            # This is required for cookies to be properly associated
            logger.info("Navigating to LinkedIn to set cookie context...")
            await self._page.goto("https://www.linkedin.com", wait_until="domcontentloaded", timeout=30000)
            await self._human_delay(1000, 2000)

            # Add the li_at cookie to the browser context
            cookie_value = li_at_cookie.strip()
            logger.info(f"Injecting cookie (length={len(cookie_value)}, starts={cookie_value[:20] if len(cookie_value) > 20 else cookie_value}...)")

            await self._context.add_cookies([
                {
                    "name": "li_at",
                    "value": cookie_value,
                    "domain": ".linkedin.com",
                    "path": "/",
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "None",
                }
            ])

            logger.info("LinkedIn cookie injected successfully")

            # Reload the page to apply the cookie
            await self._page.reload(wait_until="networkidle", timeout=30000)
            await self._human_delay(2000, 3000)

            return True

        except Exception as e:
            logger.error(f"Failed to inject cookie: {e}")
            return False

        finally:
            self.set_busy(False)

    async def navigate_to_login(self) -> None:
        """Navigate to LinkedIn login page for manual login.

        This opens the login page in the visible browser so the user
        can log in manually (handling CAPTCHAs, 2FA, etc).
        """
        # Always launch in visible mode for manual login
        # This will restart the browser if it's currently running in headless mode
        await self.launch(headless=False)

        try:
            self.set_busy(True)

            logger.info(f"Navigating to LinkedIn login page: {self.LOGIN_URL}")
            await self._page.goto(self.LOGIN_URL)
            await self._page.wait_for_load_state("networkidle", timeout=15000)

            logger.info("Navigated to LinkedIn login page for manual login - browser window should be visible")

        except Exception as e:
            logger.error(f"Failed to navigate to login: {e}")
            raise

        finally:
            self.set_busy(False)

    async def submit_verification_code(self, code: str) -> LinkedInStatus:
        """Submit email/SMS verification code."""
        if not self.is_running():
            return LinkedInStatus.ERROR

        try:
            self.set_busy(True)

            # Log current URL for debugging
            logger.info(f"Verification page URL: {self._page.url}")

            # Try multiple selectors for the verification code input
            code_input_selectors = [
                'input[name="pin"]',
                'input[id="input__email_verification_pin"]',
                'input#input__email_verification_pin',
                'input.input_verification_pin',
                'input[type="text"][name="pin"]',
                'input[aria-label*="verification"]',
                'input[aria-label*="code"]',
                '#captcha-internal input',
                'input.verification-code-input',
            ]

            code_input = None
            for selector in code_input_selectors:
                code_input = await self._page.query_selector(selector)
                if code_input:
                    logger.info(f"Found code input with selector: {selector}")
                    break

            if not code_input:
                # Try to find any visible text input on the page
                all_inputs = await self._page.query_selector_all('input[type="text"], input:not([type])')
                for inp in all_inputs:
                    if await inp.is_visible():
                        code_input = inp
                        logger.info("Found code input via fallback (visible text input)")
                        break

            if not code_input:
                # Take screenshot for debugging
                page_content = await self._page.content()
                logger.error(f"Could not find verification code input. Page URL: {self._page.url}")
                logger.debug(f"Page content snippet: {page_content[:2000]}")
                return LinkedInStatus.ERROR

            # Clear and fill the code
            await code_input.click()
            await code_input.fill("")
            await self._human_delay(300, 500)
            await code_input.fill(code)
            await self._human_delay(500, 1000)

            # Try multiple selectors for the submit button
            submit_selectors = [
                'button[type="submit"]',
                'button.btn__primary--large',
                'button[data-litms-control-urn*="submit"]',
                '#email-pin-submit-button',
                'button:has-text("Submit")',
                'button:has-text("Valider")',
                'button:has-text("Verify")',
                'form button',
            ]

            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = await self._page.query_selector(selector)
                    if submit_button and await submit_button.is_visible():
                        logger.info(f"Found submit button with selector: {selector}")
                        break
                except Exception:
                    continue

            if submit_button:
                await submit_button.click()
            else:
                # Try pressing Enter as fallback
                logger.info("No submit button found, pressing Enter")
                await code_input.press("Enter")

            # Wait for navigation
            await self._page.wait_for_load_state("networkidle", timeout=20000)
            await self._human_delay(2000, 3000)

            # Check result - may need multiple checks as LinkedIn sometimes has intermediate pages
            current_url = self._page.url
            logger.info(f"Post-verification URL (1st check): {current_url}")

            # If on /verify page, there might be a "Continue" or confirmation button
            if "/verify" in current_url.lower() or "/challenge" in current_url.lower():
                logger.info("On verify/challenge page, looking for continue button...")
                await self._human_delay(2000, 3000)

                # Look for any continue/confirm buttons on the page
                continue_selectors = [
                    'button[type="submit"]',
                    'button:has-text("Continue")',
                    'button:has-text("Continuer")',
                    'button:has-text("Done")',
                    'button:has-text("Terminé")',
                    'button:has-text("Confirm")',
                    'button:has-text("Confirmer")',
                    'button.btn__primary--large',
                    'a.btn__primary--large',
                    '[data-litms-control-urn*="continue"]',
                    '[data-litms-control-urn*="done"]',
                ]

                for selector in continue_selectors:
                    try:
                        btn = await self._page.query_selector(selector)
                        if btn and await btn.is_visible():
                            logger.info(f"Found continue button with selector: {selector}")
                            await btn.click()
                            await self._page.wait_for_load_state("networkidle", timeout=15000)
                            await self._human_delay(2000, 3000)
                            current_url = self._page.url
                            logger.info(f"After clicking continue: {current_url}")
                            break
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                        continue

                # Check if we're now logged in
                if self._is_feed_url(current_url) or self._is_logged_in_url(current_url):
                    logger.info("Verification successful after clicking continue")
                    return LinkedInStatus.CONNECTED

                # If still not on feed, try navigating there
                if not self._is_feed_url(current_url):
                    try:
                        logger.info("Trying to navigate to feed...")
                        await self._page.goto(self.FEED_URL, timeout=15000)
                        await self._page.wait_for_load_state("networkidle", timeout=10000)
                        current_url = self._page.url
                        logger.info(f"After navigating to feed: {current_url}")
                    except Exception as e:
                        logger.warning(f"Could not navigate to feed: {e}")

            if self._is_feed_url(current_url) or self._is_logged_in_url(current_url):
                logger.info("Verification successful - user is logged in")
                return LinkedInStatus.CONNECTED

            # Check if there's an error message on the page
            error_msg = await self._page.query_selector('.form__label--error, .alert-error, [role="alert"]')
            if error_msg:
                error_text = await error_msg.text_content()
                logger.warning(f"Error message on page: {error_text}")
                return LinkedInStatus.NEED_EMAIL_CODE

            # Check if still on verification page (wrong code or need another code)
            if self._is_challenge_url(current_url):
                # Check if there's still a pin input (needs another code)
                pin_input = await self._page.query_selector('input[name="pin"]')
                if pin_input:
                    logger.warning("Still on verification page - code may be incorrect or new code needed")
                    return LinkedInStatus.NEED_EMAIL_CODE
                else:
                    logger.warning("On checkpoint page but no pin input - may need manual intervention")
                    return LinkedInStatus.NEED_MANUAL_LOGIN

            logger.warning(f"Verification failed or additional step required. URL: {current_url}")
            return LinkedInStatus.ERROR

        except Exception as e:
            logger.error(f"Verification error: {e}")
            return LinkedInStatus.ERROR

        finally:
            self.set_busy(False)

    async def validate_session(self) -> bool:
        """Check if current session is still valid."""
        if not self.is_running():
            return False

        try:
            self.set_busy(True)

            # First check current URL without navigating
            current_url = self._page.url
            logger.info(f"Current page URL: {current_url}")

            # If already on a logged-in page, we're good
            if self._is_feed_url(current_url) or self._is_logged_in_url(current_url):
                logger.info("Already on logged-in page - session valid")
                return True

            # Navigate to feed and check if we're still logged in
            logger.info("Navigating to feed to validate session...")
            await self._page.goto(self.FEED_URL)
            await self._page.wait_for_load_state("networkidle", timeout=15000)

            current_url = self._page.url
            logger.info(f"After navigation URL: {current_url}")

            # Check if we ended up on feed or got redirected to login
            is_valid = self._is_feed_url(current_url) or self._is_logged_in_url(current_url)

            logger.info(f"Session validation: {'valid' if is_valid else 'invalid'}")
            return is_valid

        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return False

        finally:
            self.set_busy(False)

    async def search_people(self, query: str) -> list[LinkedInContact]:
        """Search for people on LinkedIn."""
        if not self.is_running():
            raise RuntimeError("Browser not running")

        try:
            self.set_busy(True)

            # Build search URL with URL encoding
            from urllib.parse import quote
            search_url = f"{self.SEARCH_URL}?keywords={quote(query)}&origin=GLOBAL_SEARCH_HEADER"
            logger.info(f"Searching: {search_url}")

            await self._page.goto(search_url)
            await self._page.wait_for_load_state("networkidle", timeout=20000)
            await self._human_delay(3000, 5000)

            # Wait for results to load - try multiple selectors
            results_selectors = [
                ".search-results-container",
                ".reusable-search__result-container",
                "[data-view-name='search-entity-result-universal-template']",
                ".scaffold-finite-scroll__content",
                "ul.reusable-search__entity-result-list",
                ".search-results__list",
            ]

            results_found = False
            for selector in results_selectors:
                try:
                    await self._page.wait_for_selector(selector, timeout=5000)
                    logger.info(f"Found results container with selector: {selector}")
                    results_found = True
                    break
                except Exception:
                    continue

            if not results_found:
                logger.warning("No results container found, trying to extract anyway...")

            # Simulate reading the page before extracting data
            await self._simulate_reading(1.5, 3.0)

            # Scroll down to load more results and simulate human behavior
            for _ in range(random.randint(2, 4)):
                await self._human_scroll("down")
                await self._simulate_reading(0.5, 1.5)

            # Scroll back up to see all results
            await self._human_scroll("up", random.randint(200, 400))
            await self._human_delay(1000, 2000)

            # Extract contacts with multiple selector strategies
            contacts_data = await self._page.evaluate("""
                () => {
                    const results = [];

                    // Strategy 1: entity-result (older layout)
                    document.querySelectorAll('.entity-result, .entity-result__item').forEach((el) => {
                        const nameEl = el.querySelector('.entity-result__title-text a span[aria-hidden="true"]') ||
                                      el.querySelector('.entity-result__title-text a span:not(.visually-hidden)') ||
                                      el.querySelector('[data-anonymize="person-name"]');
                        const titleEl = el.querySelector('.entity-result__primary-subtitle') ||
                                       el.querySelector('[data-anonymize="title"]');
                        const locationEl = el.querySelector('.entity-result__secondary-subtitle') ||
                                          el.querySelector('[data-anonymize="location"]');
                        const linkEl = el.querySelector('.entity-result__title-text a') ||
                                      el.querySelector('a[href*="/in/"]');

                        if (nameEl) {
                            results.push({
                                name: nameEl.textContent.trim(),
                                title: titleEl ? titleEl.textContent.trim() : null,
                                location: locationEl ? locationEl.textContent.trim() : null,
                                profile_url: linkEl ? linkEl.href.split('?')[0] : null,
                            });
                        }
                    });

                    // Strategy 2: reusable-search results (newer layout)
                    if (results.length === 0) {
                        document.querySelectorAll('li.reusable-search__result-container, [data-view-name="search-entity-result-universal-template"]').forEach((el) => {
                            const nameEl = el.querySelector('span[aria-hidden="true"]') ||
                                          el.querySelector('.artdeco-entity-lockup__title');
                            const titleEl = el.querySelector('.entity-result__primary-subtitle') ||
                                           el.querySelector('.artdeco-entity-lockup__subtitle');
                            const locationEl = el.querySelector('.entity-result__secondary-subtitle') ||
                                              el.querySelector('.artdeco-entity-lockup__caption');
                            const linkEl = el.querySelector('a[href*="/in/"]');

                            if (nameEl && nameEl.textContent.trim()) {
                                results.push({
                                    name: nameEl.textContent.trim(),
                                    title: titleEl ? titleEl.textContent.trim() : null,
                                    location: locationEl ? locationEl.textContent.trim() : null,
                                    profile_url: linkEl ? linkEl.href.split('?')[0] : null,
                                });
                            }
                        });
                    }

                    // Strategy 3: Generic search results
                    if (results.length === 0) {
                        document.querySelectorAll('[data-chameleon-result-urn]').forEach((el) => {
                            const nameEl = el.querySelector('span[aria-hidden="true"]');
                            const linkEl = el.querySelector('a[href*="/in/"]');

                            if (nameEl && nameEl.textContent.trim()) {
                                results.push({
                                    name: nameEl.textContent.trim(),
                                    title: null,
                                    location: null,
                                    profile_url: linkEl ? linkEl.href.split('?')[0] : null,
                                });
                            }
                        });
                    }

                    return results;
                }
            """)

            contacts = [self._parse_contact(data) for data in contacts_data]
            logger.info(f"Found {len(contacts)} contacts for query: {query}")

            return contacts

        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

        finally:
            self.set_busy(False)

    # URL detection helpers
    def _is_feed_url(self, url: str) -> bool:
        """Check if URL is the LinkedIn feed (logged in)."""
        return "/feed" in url.lower()

    def _is_login_url(self, url: str) -> bool:
        """Check if URL is the login page."""
        return "/login" in url.lower() or "/uas/login" in url.lower()

    def _is_challenge_url(self, url: str) -> bool:
        """Check if URL is a challenge/verification page."""
        return "/checkpoint" in url.lower()

    def _is_logged_in_url(self, url: str) -> bool:
        """Check if URL indicates user is logged in (feed, home, mynetwork, etc)."""
        logged_in_paths = ["/feed", "/mynetwork", "/jobs", "/messaging", "/notifications", "/in/"]
        return any(path in url.lower() for path in logged_in_paths)

    async def _is_email_verification_page(self) -> bool:
        """Check if current page is email verification."""
        pin_input = await self._page.query_selector('input[name="pin"]')
        email_pin = await self._page.query_selector('input[id="input__email_verification_pin"]')
        return pin_input is not None or email_pin is not None

    # Contact parsing
    def _parse_contact(self, raw_data: dict[str, Any]) -> LinkedInContact:
        """Parse raw contact data into LinkedInContact."""
        def clean_value(value: str | None) -> str | None:
            if value is None:
                return None
            cleaned = value.strip()
            return cleaned if cleaned else None

        return LinkedInContact(
            name=clean_value(raw_data.get("name")),
            title=clean_value(raw_data.get("title")),
            company=clean_value(raw_data.get("company")),
            location=clean_value(raw_data.get("location")),
            profile_url=clean_value(raw_data.get("profile_url")),
        )

    # Human-like behavior
    def _get_random_delay(self, min_ms: int = 2000, max_ms: int = 5000) -> int:
        """Get a random delay in milliseconds with human-like variation."""
        base_delay = random.randint(min_ms, max_ms)

        # 20% chance of a longer "distraction" pause (humans get distracted)
        if random.random() < 0.2:
            base_delay += random.randint(1000, 3000)

        # Add micro-variations for naturalness
        variation = random.randint(-100, 100)
        return max(min_ms, base_delay + variation)

    async def _human_delay(self, min_ms: int = 2000, max_ms: int = 5000) -> None:
        """Wait for a random human-like delay."""
        delay_ms = self._get_random_delay(min_ms, max_ms)
        await asyncio.sleep(delay_ms / 1000)

    async def _human_type(self, element, text: str) -> None:
        """Type text character by character with human-like delays."""
        await element.click()
        await asyncio.sleep(random.uniform(0.1, 0.3))

        for char in text:
            await element.type(char, delay=random.randint(50, 150))
            # Occasional longer pause (like thinking)
            if random.random() < 0.1:
                await asyncio.sleep(random.uniform(0.2, 0.5))

    async def _human_scroll(self, direction: str = "down", amount: int | None = None) -> None:
        """Scroll the page like a human would.

        Args:
            direction: "down" or "up"
            amount: Pixels to scroll. If None, uses random amount.
        """
        if amount is None:
            amount = random.randint(300, 700)

        if direction == "up":
            amount = -amount

        # Smooth scroll with multiple small steps
        steps = random.randint(3, 6)
        step_amount = amount // steps

        for _ in range(steps):
            await self._page.evaluate(f"window.scrollBy(0, {step_amount})")
            await asyncio.sleep(random.uniform(0.05, 0.15))

        # Small pause after scrolling (human reads content)
        await asyncio.sleep(random.uniform(0.3, 0.8))

    async def _human_mouse_move(self, x: int, y: int) -> None:
        """Move mouse to position with human-like trajectory."""
        # Get current mouse position (approximate center if unknown)
        current_x = random.randint(400, 600)
        current_y = random.randint(300, 500)

        # Calculate distance and steps
        distance = ((x - current_x) ** 2 + (y - current_y) ** 2) ** 0.5
        steps = max(5, int(distance / 50))

        for i in range(steps):
            # Add slight curve/randomness to movement
            progress = (i + 1) / steps
            # Ease-out curve for natural deceleration
            eased_progress = 1 - (1 - progress) ** 2

            next_x = current_x + (x - current_x) * eased_progress + random.randint(-2, 2)
            next_y = current_y + (y - current_y) * eased_progress + random.randint(-2, 2)

            await self._page.mouse.move(next_x, next_y)
            await asyncio.sleep(random.uniform(0.01, 0.03))

    async def _simulate_reading(self, min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
        """Simulate reading content on the page."""
        read_time = random.uniform(min_seconds, max_seconds)

        # Occasionally do small scrolls while "reading"
        if random.random() < 0.3:
            await self._human_scroll("down", random.randint(100, 200))

        await asyncio.sleep(read_time)
