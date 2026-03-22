"""
Interactive Browser Tools for AI Agents.
Provides full browser automation: click, fill, type, select, drag, screenshots, cookies.
"""

import json
import logging
import os
import re
from typing import Any, Literal

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeout

from .browser_session import BrowserSession, ElementRef, to_ai_friendly_error

logger = logging.getLogger(__name__)


def _get_workspace_path(config: dict[str, Any] | None) -> str | None:
    """Get the workspace path from config or RuntimeContext (including Celery task fallback)."""
    from src.services.agents.workspace_manager import get_workspace_path_from_config

    return get_workspace_path_from_config(config)


def _validate_path_in_workspace(path: str, workspace_path: str | None) -> tuple[bool, str | None]:
    """Validate that a path is within the workspace directory."""
    if not workspace_path:
        return False, "No workspace path configured. File operations require a valid workspace."

    try:
        real_path = os.path.realpath(path)
        real_workspace = os.path.realpath(workspace_path)
        real_path = real_path.removeprefix("/private")
        real_workspace = real_workspace.removeprefix("/private")

        if not (real_path.startswith(real_workspace + os.sep) or real_path == real_workspace):
            return False, f"Path '{path}' is outside the workspace directory"

        return True, None
    except Exception as e:
        return False, f"Error validating path: {str(e)}"


# Default timeout for interactions (ms)
DEFAULT_TIMEOUT = 8000
MAX_TIMEOUT = 60000
MIN_TIMEOUT = 500


def normalize_timeout(timeout_ms: int | None, default: int = DEFAULT_TIMEOUT) -> int:
    """Normalize timeout value to valid range"""
    if timeout_ms is None:
        return default
    return max(MIN_TIMEOUT, min(MAX_TIMEOUT, timeout_ms))


async def _get_session_and_page(session_id: str, page_id: str | None = None) -> tuple[BrowserSession, Page]:
    """Get browser session and page"""
    session = await BrowserSession.get_or_create(session_id)
    page = await session.get_page(page_id)
    return session, page


def _get_locator_strategies(page: Page, ref: str, state=None) -> list:
    """
    Get a list of locator strategies to try for an element.
    Returns locators in order of preference.
    """
    ref = ref.strip()
    strategies = []

    # Check if it's a stored ref (e1, e2, etc.)
    if state and re.match(r"^e\d+$", ref):
        if ref in state.element_refs:
            elem_ref = state.element_refs[ref]

            # CSS selector is most reliable for custom components
            if elem_ref.selector:
                strategies.append(("css", page.locator(elem_ref.selector)))

            # Role-based locator as fallback
            locator = page.get_by_role(elem_ref.role, name=elem_ref.name)
            if elem_ref.nth == 0:
                strategies.append(("role", locator.first))
            else:
                strategies.append(("role", locator.nth(elem_ref.nth)))

            # For combobox/listbox, also try without name (in case accessible name differs)
            if elem_ref.role in ("combobox", "listbox"):
                role_locator = page.get_by_role(elem_ref.role)
                if elem_ref.nth == 0:
                    strategies.append(("role_no_name", role_locator.first))
                else:
                    strategies.append(("role_no_name", role_locator.nth(elem_ref.nth)))

            return strategies

    # For other ref types, return single strategy
    # Check if it's a role:name format
    role_match = re.match(r"^(\w+):(.+)$", ref)
    if role_match:
        role, name = role_match.groups()
        strategies.append(("role", page.get_by_role(role, name=name)))
        return strategies

    # Check for text-based locator
    if ref.startswith("text="):
        strategies.append(("text", page.get_by_text(ref[5:])))
        return strategies

    # Check for label-based locator
    if ref.startswith("label="):
        strategies.append(("label", page.get_by_label(ref[6:])))
        return strategies

    # Check for placeholder-based locator
    if ref.startswith("placeholder="):
        strategies.append(("placeholder", page.get_by_placeholder(ref[12:])))
        return strategies

    # Default to CSS selector
    strategies.append(("css", page.locator(ref)))
    return strategies


def _resolve_locator(page: Page, ref: str, state=None):
    """
    Resolve a ref to a Playwright locator.
    Supports:
    - CSS selectors: "#id", ".class", "div"
    - Role refs: "button:Login", "textbox:Email"
    - Stored refs: "e1", "e2" (from snapshot)
    """
    strategies = _get_locator_strategies(page, ref, state)
    if strategies:
        return strategies[0][1]  # Return the first (preferred) locator
    return page.locator(ref)  # Fallback to CSS selector


def _resolve_frame_locator(page: Page, frame_selector: str, ref: str, state=None):
    """
    Resolve a ref scoped to a specific iframe via frame_locator.
    frame_selector: CSS selector for the iframe, e.g. "iframe[src*='magic.link']"
    ref: same ref formats as _resolve_locator
    """
    fl = page.frame_locator(frame_selector)
    ref = ref.strip()

    if state and re.match(r"^e\d+$", ref) and ref in state.element_refs:
        elem_ref = state.element_refs[ref]
        if elem_ref.selector:
            return fl.locator(elem_ref.selector)
        locator = fl.get_by_role(elem_ref.role, name=elem_ref.name)
        return locator.first if elem_ref.nth == 0 else locator.nth(elem_ref.nth)

    role_match = re.match(r"^(\w+):(.+)$", ref)
    if role_match:
        role, name = role_match.groups()
        return fl.get_by_role(role, name=name)

    if ref.startswith("text="):
        return fl.get_by_text(ref[5:])
    if ref.startswith("label="):
        return fl.get_by_label(ref[6:])
    if ref.startswith("placeholder="):
        return fl.get_by_placeholder(ref[12:])

    return fl.locator(ref)


# =============================================================================
# NAVIGATION
# =============================================================================


async def internal_browser_navigate(
    url: str,
    session_id: str = "default",
    page_id: str | None = None,
    wait_until: Literal["load", "domcontentloaded", "networkidle"] = "load",
    timeout_ms: int | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Navigate to a URL in the browser.

    Args:
        url: The URL to navigate to
        session_id: Browser session ID (default: "default")
        page_id: Specific page/tab ID (optional)
        wait_until: Wait condition - "load", "domcontentloaded", or "networkidle"
        timeout_ms: Navigation timeout in milliseconds

    Returns:
        Dict with navigation result including final URL and page title

    Example:
        result = await internal_browser_navigate(
            url="https://example.com",
            wait_until="networkidle"
        )
    """
    try:
        session, page = await _get_session_and_page(session_id, page_id)
        timeout = normalize_timeout(timeout_ms, 30000)

        response = await page.goto(url, wait_until=wait_until, timeout=timeout)

        return {
            "success": True,
            "url": page.url,
            "title": await page.title(),
            "status": response.status if response else None,
            "session_id": session_id,
            "page_id": session.current_page_id,
        }

    except PlaywrightTimeout:
        return {"success": False, "error": f"Navigation timeout for {url}"}
    except Exception as e:
        logger.error(f"Navigation error: {e}")
        return {"success": False, "error": to_ai_friendly_error(e, url)}


# =============================================================================
# SNAPSHOT - AI-FRIENDLY PAGE STATE
# =============================================================================


async def internal_browser_snapshot(
    session_id: str = "default",
    page_id: str | None = None,
    interactive_only: bool = True,
    max_elements: int = 150,
    include_text: bool = True,
    frame_selector: str | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Get AI-friendly snapshot of the page with element refs.

    Args:
        session_id: Browser session ID
        page_id: Specific page/tab ID
        interactive_only: Only include interactive elements (default: True)
        max_elements: Maximum elements to return (default: 150)
        include_text: Include visible text content (default: True)
        frame_selector: CSS selector for a cross-origin iframe to snapshot instead of the main page,
            e.g. "iframe[src*='magic.link']". Use internal_browser_list_frames first to discover frames.

    Returns:
        Dict with:
        - snapshot: Human-readable page state with refs
        - refs: Map of ref IDs to element details
        - url: Current page URL
        - title: Page title

    Example:
        result = await internal_browser_snapshot(interactive_only=True)
        # Returns:
        # {
        #   "snapshot": "button \"Login\" [ref=e1]\\ntextbox \"Email\" [ref=e2]...",
        #   "refs": {"e1": {"role": "button", "name": "Login"}, ...}
        # }

    Use refs in subsequent actions:
        await internal_browser_click(ref="e1")  # Click the Login button
    """
    try:
        session, page = await _get_session_and_page(session_id, page_id)
        state = session.get_page_state(page)

        # Clear previous refs
        state.element_refs.clear()
        state.next_ref_id = 0

        # Get interactive elements using accessibility tree
        snapshot_lines = []
        refs = {}

        # Define interactive roles
        interactive_roles = [
            "button",
            "link",
            "textbox",
            "checkbox",
            "radio",
            "combobox",
            "listbox",
            "option",
            "menuitem",
            "tab",
            "switch",
            "slider",
            "spinbutton",
            "searchbox",
        ]

        # Resolve the locator root: frame or page
        frame_root = page.frame_locator(frame_selector) if frame_selector else None

        # Get elements by role
        elements_found = 0
        for role in interactive_roles:
            if elements_found >= max_elements:
                break

            try:
                locator = frame_root.get_by_role(role) if frame_root else page.get_by_role(role)
                count = await locator.count()

                for i in range(min(count, max_elements - elements_found)):
                    try:
                        element = locator.nth(i)

                        # Check if visible
                        if not await element.is_visible():
                            continue

                        # Get element info
                        name = None
                        try:
                            name = await element.get_attribute("aria-label")
                            if not name:
                                name = await element.inner_text()
                                if name:
                                    name = name.strip()[:50]  # Limit text length
                        except Exception:
                            pass

                        # Generate ref
                        ref_id = state.generate_ref_id()

                        # Build a unique CSS selector for this element as fallback
                        css_selector = None
                        try:
                            css_selector = await element.evaluate("""el => {
                                // Try to build a unique selector for this element
                                if (el.id) {
                                    return '#' + CSS.escape(el.id);
                                }

                                // Try data-testid or data-cy attributes
                                const testId = el.getAttribute('data-testid') || el.getAttribute('data-cy') || el.getAttribute('data-test');
                                if (testId) {
                                    return '[data-testid="' + testId + '"], [data-cy="' + testId + '"], [data-test="' + testId + '"]';
                                }

                                // Build a path-based selector
                                const path = [];
                                let current = el;
                                while (current && current.nodeType === Node.ELEMENT_NODE) {
                                    let selector = current.tagName.toLowerCase();

                                    // Add unique attributes
                                    if (current.id) {
                                        selector = '#' + CSS.escape(current.id);
                                        path.unshift(selector);
                                        break;
                                    }

                                    // Add class if unique among siblings
                                    if (current.className && typeof current.className === 'string') {
                                        const classes = current.className.trim().split(/\\s+/).filter(c => c && !c.startsWith('_'));
                                        if (classes.length > 0) {
                                            selector += '.' + classes.slice(0, 2).map(c => CSS.escape(c)).join('.');
                                        }
                                    }

                                    // Add nth-of-type if needed
                                    const parent = current.parentElement;
                                    if (parent) {
                                        const siblings = Array.from(parent.children).filter(c => c.tagName === current.tagName);
                                        if (siblings.length > 1) {
                                            const index = siblings.indexOf(current) + 1;
                                            selector += ':nth-of-type(' + index + ')';
                                        }
                                    }

                                    path.unshift(selector);
                                    current = current.parentElement;

                                    // Limit path depth
                                    if (path.length >= 5) break;
                                }

                                return path.join(' > ');
                            }""")
                        except Exception as selector_err:
                            logger.debug(f"Could not generate CSS selector for {role}[{i}]: {selector_err}")

                        # Build selector for this element
                        elem_ref = ElementRef(role=role, name=name, nth=i, selector=css_selector)
                        state.element_refs[ref_id] = elem_ref
                        refs[ref_id] = {"role": role, "name": name, "nth": i, "selector": css_selector}

                        # Format for snapshot
                        name_str = f' "{name}"' if name else ""
                        snapshot_lines.append(f"{role}{name_str} [ref={ref_id}]")
                        elements_found += 1

                    except Exception as e:
                        logger.debug(f"Error getting element {role}[{i}]: {e}")
                        continue

            except Exception as e:
                logger.debug(f"Error getting role {role}: {e}")
                continue

        # Optionally include page text
        text_content = ""
        if include_text:
            try:
                text_content = await page.evaluate("document.body.innerText")
                if len(text_content) > 5000:
                    text_content = text_content[:5000] + "\n...[truncated]"
            except Exception:
                pass

        snapshot = "\n".join(snapshot_lines)

        result = {
            "success": True,
            "snapshot": snapshot,
            "refs": refs,
            "ref_count": len(refs),
            "url": page.url,
            "title": await page.title(),
            "text_content": text_content if include_text else None,
            "session_id": session_id,
            "page_id": session.current_page_id,
        }
        if frame_selector:
            result["frame_selector"] = frame_selector
        return result

    except Exception as e:
        logger.error(f"Snapshot error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# CLICK
# =============================================================================


async def internal_browser_click(
    ref: str,
    session_id: str = "default",
    page_id: str | None = None,
    double_click: bool = False,
    button: Literal["left", "right", "middle"] = "left",
    modifiers: list[str] | None = None,
    timeout_ms: int | None = None,
    frame_selector: str | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Click an element on the page.

    Args:
        ref: Element reference - can be:
            - Snapshot ref: "e1", "e2" (from internal_browser_snapshot)
            - Role:name: "button:Login", "link:Sign up"
            - CSS selector: "#submit-btn", ".nav-link"
            - Text: "text=Click here"
            - Label: "label=Email"
        session_id: Browser session ID
        page_id: Specific page/tab ID
        double_click: Perform double-click (default: False)
        button: Mouse button - "left", "right", "middle"
        modifiers: Keyboard modifiers - ["Alt", "Control", "Meta", "Shift"]
        timeout_ms: Click timeout in milliseconds

    Returns:
        Dict with click result

    Example:
        # Click using snapshot ref
        await internal_browser_click(ref="e1")

        # Click using role:name
        await internal_browser_click(ref="button:Submit")

        # Right-click with modifier
        await internal_browser_click(ref="e3", button="right", modifiers=["Control"])
    """
    try:
        session, page = await _get_session_and_page(session_id, page_id)
        state = session.get_page_state(page)
        timeout = normalize_timeout(timeout_ms)

        # If frame_selector provided, resolve within that frame only
        if frame_selector:
            strategies = [("frame", _resolve_frame_locator(page, frame_selector, ref, state))]
        else:
            # Get all locator strategies to try
            strategies = _get_locator_strategies(page, ref, state)
            if not strategies:
                strategies = [("css", page.locator(ref))]

        click_opts = {"timeout": timeout, "button": button}
        if modifiers:
            click_opts["modifiers"] = modifiers

        last_error = None
        for strategy_name, locator in strategies:
            try:
                logger.debug(f"Trying click with strategy '{strategy_name}' for ref={ref}")

                # Try to scroll into view first
                try:
                    await locator.scroll_into_view_if_needed(timeout=timeout // 2)
                except Exception:
                    pass  # Continue even if scroll fails

                # Try normal click first
                try:
                    if double_click:
                        await locator.dblclick(**click_opts)
                    else:
                        await locator.click(**click_opts)
                except Exception as click_err:
                    # If normal click fails, try with force (bypasses actionability checks)
                    error_msg = str(click_err).lower()
                    if "timeout" in error_msg or "intercept" in error_msg or "not visible" in error_msg:
                        logger.debug(f"Normal click failed with {strategy_name}, trying force click: {click_err}")
                        force_opts = {**click_opts, "force": True}
                        if double_click:
                            await locator.dblclick(**force_opts)
                        else:
                            await locator.click(**force_opts)
                    else:
                        raise click_err

                # Success!
                logger.debug(f"Click succeeded with strategy '{strategy_name}'")
                return {
                    "success": True,
                    "action": "double_click" if double_click else "click",
                    "ref": ref,
                    "strategy": strategy_name,
                    "url": page.url,
                    "session_id": session_id,
                }

            except Exception as e:
                last_error = e
                logger.debug(f"Strategy '{strategy_name}' failed: {e}")
                continue

        # All strategies failed
        raise last_error or Exception(f"Could not click element: {ref}")

    except Exception as e:
        logger.error(f"Click error: {e}")
        return {"success": False, "error": to_ai_friendly_error(e, ref)}


# =============================================================================
# FILL / TYPE
# =============================================================================


async def internal_browser_fill(
    ref: str,
    text: str,
    session_id: str = "default",
    page_id: str | None = None,
    clear_first: bool = True,
    timeout_ms: int | None = None,
    frame_selector: str | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Fill text into an input field (replaces existing content).

    For combobox/dropdown elements, this automatically clicks the dropdown
    and selects the option by text instead of using fill().

    Args:
        ref: Element reference (see internal_browser_click for formats)
        text: Text to fill (for dropdowns, this is the option text to select)
        session_id: Browser session ID
        page_id: Specific page/tab ID
        clear_first: Clear field before filling (default: True)
        timeout_ms: Timeout in milliseconds

    Returns:
        Dict with fill result

    Example:
        await internal_browser_fill(ref="e2", text="user@example.com")
        await internal_browser_fill(ref="textbox:Password", text="secret123")
        await internal_browser_fill(ref="e5", text="United States")  # Works for dropdowns too
    """
    try:
        session, page = await _get_session_and_page(session_id, page_id)
        state = session.get_page_state(page)
        timeout = normalize_timeout(timeout_ms)

        # If frame_selector provided, resolve within that frame only
        if frame_selector:
            strategies = [("frame", _resolve_frame_locator(page, frame_selector, ref, state))]
        else:
            # Get all locator strategies
            strategies = _get_locator_strategies(page, ref, state)
            if not strategies:
                strategies = [("css", page.locator(ref))]

        # Check if this is a combobox/listbox element (custom dropdown)
        is_combobox = False
        if state and re.match(r"^e\d+$", ref):
            elem_ref = state.element_refs.get(ref)
            logger.debug(f"Fill: checking ref={ref}, elem_ref={elem_ref}, role={elem_ref.role if elem_ref else 'N/A'}")
            if elem_ref and elem_ref.role in ("combobox", "listbox"):
                is_combobox = True
                logger.info(f"Detected combobox element: ref={ref}, role={elem_ref.role}")
        elif ref.startswith(("combobox:", "listbox:")):
            is_combobox = True
            logger.info(f"Detected combobox from ref prefix: ref={ref}")

        if is_combobox:
            # Handle custom dropdown: click to open, then select option
            logger.debug(f"Detected combobox element {ref}, using click-based selection")

            # Try to click the dropdown using multiple strategies
            click_success = False
            for strategy_name, strategy_locator in strategies:
                try:
                    logger.debug(f"Trying to open combobox with strategy '{strategy_name}'")
                    await strategy_locator.click(timeout=timeout)
                    click_success = True
                    logger.debug(f"Combobox opened with strategy '{strategy_name}'")
                    break
                except Exception as click_err:
                    logger.debug(f"Strategy '{strategy_name}' failed to open combobox: {click_err}")
                    continue

            if not click_success:
                return {
                    "success": False,
                    "error": f"Could not open dropdown: {ref}. All locator strategies failed.",
                }

            # Wait a moment for dropdown to open
            await page.wait_for_timeout(300)

            # Try multiple strategies to find and click the option
            option_found = False

            # Strategy 1: Look for option role with exact text
            try:
                option = page.get_by_role("option", name=text, exact=True)
                if await option.count() > 0:
                    await option.first.click(timeout=timeout)
                    option_found = True
            except Exception:
                pass

            # Strategy 2: Look for option role with partial text match
            if not option_found:
                try:
                    option = page.get_by_role("option", name=text)
                    if await option.count() > 0:
                        await option.first.click(timeout=timeout)
                        option_found = True
                except Exception:
                    pass

            # Strategy 3: Look for listitem role
            if not option_found:
                try:
                    option = page.get_by_role("listitem").filter(has_text=text)
                    if await option.count() > 0:
                        await option.first.click(timeout=timeout)
                        option_found = True
                except Exception:
                    pass

            # Strategy 4: Look for any clickable text within dropdown
            if not option_found:
                try:
                    option = page.get_by_text(text, exact=True)
                    if await option.count() > 0:
                        await option.first.click(timeout=timeout)
                        option_found = True
                except Exception:
                    pass

            # Strategy 5: Partial text match
            if not option_found:
                try:
                    option = page.get_by_text(text)
                    if await option.count() > 0:
                        await option.first.click(timeout=timeout)
                        option_found = True
                except Exception:
                    pass

            if not option_found:
                # Press Escape to close dropdown and report failure
                await page.keyboard.press("Escape")
                return {
                    "success": False,
                    "error": f"Could not find option '{text}' in dropdown. Try using internal_browser_snapshot to see available options.",
                    "ref": ref,
                }

            return {
                "success": True,
                "action": "select_dropdown",
                "ref": ref,
                "selected": text,
                "session_id": session_id,
            }

        # Standard text input fill - try multiple strategies
        last_error = None
        for strategy_name, strategy_locator in strategies:
            try:
                logger.debug(f"Trying fill with strategy '{strategy_name}' for ref={ref}")
                if clear_first:
                    await strategy_locator.clear(timeout=timeout)

                await strategy_locator.fill(text, timeout=timeout)

                logger.debug(f"Fill succeeded with strategy '{strategy_name}'")
                return {
                    "success": True,
                    "action": "fill",
                    "ref": ref,
                    "text_length": len(text),
                    "strategy": strategy_name,
                    "session_id": session_id,
                }
            except Exception as e:
                last_error = e
                logger.debug(f"Strategy '{strategy_name}' failed for fill: {e}")
                continue

        # All strategies failed
        raise last_error or Exception(f"Could not fill element: {ref}")

    except Exception as e:
        logger.error(f"Fill error: {e}")
        return {"success": False, "error": to_ai_friendly_error(e, ref)}


async def internal_browser_type(
    ref: str,
    text: str,
    session_id: str = "default",
    page_id: str | None = None,
    delay_ms: int = 0,
    submit: bool = False,
    timeout_ms: int | None = None,
    frame_selector: str | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Type text character by character (simulates real typing).

    Args:
        ref: Element reference
        text: Text to type
        session_id: Browser session ID
        page_id: Specific page/tab ID
        delay_ms: Delay between keystrokes in ms (default: 0, use 50-100 for realistic typing)
        submit: Press Enter after typing (default: False)
        timeout_ms: Timeout in milliseconds

    Returns:
        Dict with type result

    Example:
        # Type slowly like a human
        await internal_browser_type(ref="e2", text="search query", delay_ms=50, submit=True)
    """
    try:
        session, page = await _get_session_and_page(session_id, page_id)
        state = session.get_page_state(page)
        timeout = normalize_timeout(timeout_ms)

        if frame_selector:
            locator = _resolve_frame_locator(page, frame_selector, ref, state)
        else:
            locator = _resolve_locator(page, ref, state)

        # Click to focus
        await locator.click(timeout=timeout)

        # Type with delay
        await locator.type(text, delay=delay_ms, timeout=timeout)

        if submit:
            await locator.press("Enter", timeout=timeout)

        return {
            "success": True,
            "action": "type",
            "ref": ref,
            "text_length": len(text),
            "submitted": submit,
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Type error: {e}")
        return {"success": False, "error": to_ai_friendly_error(e, ref)}


# =============================================================================
# FORM FILLING
# =============================================================================


async def internal_browser_fill_form(
    fields: list[dict[str, Any]],
    session_id: str = "default",
    page_id: str | None = None,
    submit_ref: str | None = None,
    timeout_ms: int | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Fill multiple form fields at once.

    Args:
        fields: List of field definitions:
            - {"ref": "e1", "value": "text"} for text inputs
            - {"ref": "e2", "value": True} for checkboxes
            - {"ref": "e3", "value": ["option1"]} for selects
        session_id: Browser session ID
        page_id: Specific page/tab ID
        submit_ref: Element ref to click after filling (optional)
        timeout_ms: Timeout per field in milliseconds

    Returns:
        Dict with form fill results

    Example:
        await internal_browser_fill_form(
            fields=[
                {"ref": "textbox:Email", "value": "user@example.com"},
                {"ref": "textbox:Password", "value": "secret123"},
                {"ref": "checkbox:Remember me", "value": True}
            ],
            submit_ref="button:Login"
        )
    """
    try:
        session, page = await _get_session_and_page(session_id, page_id)
        state = session.get_page_state(page)
        timeout = normalize_timeout(timeout_ms)

        results = []
        for field in fields:
            ref = field.get("ref")
            value = field.get("value")

            if not ref:
                continue

            try:
                locator = _resolve_locator(page, ref, state)

                # Check if this is a combobox/listbox element
                is_combobox = False
                if state and re.match(r"^e\d+$", ref):
                    elem_ref = state.element_refs.get(ref)
                    if elem_ref and elem_ref.role in ("combobox", "listbox"):
                        is_combobox = True
                elif ref.startswith(("combobox:", "listbox:")):
                    is_combobox = True

                # Handle different input types
                if isinstance(value, bool):
                    # Checkbox/radio
                    await locator.set_checked(value, timeout=timeout)
                elif isinstance(value, list) or is_combobox:
                    # Select/multiselect or combobox - use internal_browser_select
                    select_values = value if isinstance(value, list) else [str(value)]
                    select_result = await internal_browser_select(
                        ref=ref,
                        values=select_values,
                        session_id=session_id,
                        page_id=page_id,
                        timeout_ms=timeout_ms,
                    )
                    if not select_result.get("success"):
                        raise Exception(select_result.get("error", "Select failed"))
                else:
                    # Text input
                    await locator.fill(str(value), timeout=timeout)

                results.append({"ref": ref, "success": True})

            except Exception as e:
                results.append({"ref": ref, "success": False, "error": str(e)})

        # Submit if requested
        submit_result = None
        if submit_ref:
            try:
                submit_locator = _resolve_locator(page, submit_ref, state)
                await submit_locator.click(timeout=timeout)
                submit_result = {"ref": submit_ref, "success": True}
            except Exception as e:
                submit_result = {"ref": submit_ref, "success": False, "error": str(e)}

        success_count = sum(1 for r in results if r["success"])

        return {
            "success": success_count == len(results),
            "fields_filled": success_count,
            "fields_total": len(results),
            "results": results,
            "submit_result": submit_result,
            "url": page.url,
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Form fill error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# SELECT / CHECKBOX
# =============================================================================


async def internal_browser_select(
    ref: str,
    values: list[str],
    session_id: str = "default",
    page_id: str | None = None,
    timeout_ms: int | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Select option(s) from a dropdown/select element.

    Handles both native HTML <select> elements and custom dropdowns (combobox).
    For custom dropdowns, it clicks to open, then clicks the option by text.

    Args:
        ref: Element reference for the select element
        values: List of values or labels to select
        session_id: Browser session ID
        page_id: Specific page/tab ID
        timeout_ms: Timeout in milliseconds

    Returns:
        Dict with selection result

    Example:
        await internal_browser_select(ref="e5", values=["option1"])
        await internal_browser_select(ref="combobox:Country", values=["United States"])
    """
    try:
        session, page = await _get_session_and_page(session_id, page_id)
        state = session.get_page_state(page)
        timeout = normalize_timeout(timeout_ms)

        locator = _resolve_locator(page, ref, state)

        # First try native select_option (works for <select> elements)
        try:
            selected = await locator.select_option(values, timeout=timeout)
            return {
                "success": True,
                "action": "select",
                "ref": ref,
                "selected": selected,
                "session_id": session_id,
            }
        except Exception as native_err:
            # If native select fails, it might be a custom dropdown
            logger.debug(f"Native select_option failed, trying custom dropdown: {native_err}")

        # Handle custom dropdown: click to open, then select options
        await locator.click(timeout=timeout)
        await page.wait_for_timeout(300)

        selected_values = []
        for value in values:
            option_found = False

            # Strategy 1: Look for option role with exact text
            try:
                option = page.get_by_role("option", name=value, exact=True)
                if await option.count() > 0:
                    await option.first.click(timeout=timeout)
                    option_found = True
                    selected_values.append(value)
            except Exception:
                pass

            # Strategy 2: Look for option role with partial match
            if not option_found:
                try:
                    option = page.get_by_role("option", name=value)
                    if await option.count() > 0:
                        await option.first.click(timeout=timeout)
                        option_found = True
                        selected_values.append(value)
                except Exception:
                    pass

            # Strategy 3: Look for listitem role
            if not option_found:
                try:
                    option = page.get_by_role("listitem").filter(has_text=value)
                    if await option.count() > 0:
                        await option.first.click(timeout=timeout)
                        option_found = True
                        selected_values.append(value)
                except Exception:
                    pass

            # Strategy 4: Look for text
            if not option_found:
                try:
                    option = page.get_by_text(value, exact=True)
                    if await option.count() > 0:
                        await option.first.click(timeout=timeout)
                        option_found = True
                        selected_values.append(value)
                except Exception:
                    pass

            # Strategy 5: Partial text match
            if not option_found:
                try:
                    option = page.get_by_text(value)
                    if await option.count() > 0:
                        await option.first.click(timeout=timeout)
                        option_found = True
                        selected_values.append(value)
                except Exception:
                    pass

            if not option_found:
                logger.warning(f"Could not find option '{value}' in dropdown")

        if not selected_values:
            await page.keyboard.press("Escape")
            return {
                "success": False,
                "error": f"Could not find any of the options {values} in dropdown. Try using internal_browser_snapshot to see available options.",
                "ref": ref,
            }

        return {
            "success": True,
            "action": "select_dropdown",
            "ref": ref,
            "selected": selected_values,
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Select error: {e}")
        return {"success": False, "error": to_ai_friendly_error(e, ref)}


async def internal_browser_check(
    ref: str,
    checked: bool = True,
    session_id: str = "default",
    page_id: str | None = None,
    timeout_ms: int | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Check or uncheck a checkbox/radio button.

    Args:
        ref: Element reference
        checked: True to check, False to uncheck
        session_id: Browser session ID
        page_id: Specific page/tab ID
        timeout_ms: Timeout in milliseconds

    Returns:
        Dict with check result

    Example:
        await internal_browser_check(ref="checkbox:Remember me", checked=True)
    """
    try:
        session, page = await _get_session_and_page(session_id, page_id)
        state = session.get_page_state(page)
        timeout = normalize_timeout(timeout_ms)

        locator = _resolve_locator(page, ref, state)
        await locator.set_checked(checked, timeout=timeout)

        return {
            "success": True,
            "action": "check" if checked else "uncheck",
            "ref": ref,
            "checked": checked,
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Check error: {e}")
        return {"success": False, "error": to_ai_friendly_error(e, ref)}


# =============================================================================
# KEYBOARD
# =============================================================================


async def internal_browser_press(
    key: str,
    session_id: str = "default",
    page_id: str | None = None,
    ref: str | None = None,
    timeout_ms: int | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Press a keyboard key.

    Args:
        key: Key to press - "Enter", "Tab", "Escape", "ArrowDown", "Control+a", etc.
        session_id: Browser session ID
        page_id: Specific page/tab ID
        ref: Element to focus before pressing (optional)
        timeout_ms: Timeout in milliseconds

    Returns:
        Dict with key press result

    Example:
        await internal_browser_press(key="Enter")
        await internal_browser_press(key="Control+a", ref="e2")  # Select all in field
        await internal_browser_press(key="Escape")  # Close modal
    """
    try:
        session, page = await _get_session_and_page(session_id, page_id)
        state = session.get_page_state(page)
        timeout = normalize_timeout(timeout_ms)

        if ref:
            locator = _resolve_locator(page, ref, state)
            await locator.press(key, timeout=timeout)
        else:
            await page.keyboard.press(key)

        return {
            "success": True,
            "action": "press",
            "key": key,
            "ref": ref,
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Press error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# WAIT
# =============================================================================


async def internal_browser_wait(
    session_id: str = "default",
    page_id: str | None = None,
    time_ms: int | None = None,
    selector: str | None = None,
    text: str | None = None,
    text_gone: str | None = None,
    url_pattern: str | None = None,
    load_state: Literal["load", "domcontentloaded", "networkidle"] | None = None,
    timeout_ms: int | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Wait for various conditions.

    Args:
        session_id: Browser session ID
        page_id: Specific page/tab ID
        time_ms: Simple delay in milliseconds
        selector: Wait for CSS selector to be visible
        text: Wait for text to appear
        text_gone: Wait for text to disappear
        url_pattern: Wait for URL to match pattern (glob)
        load_state: Wait for load state
        timeout_ms: Maximum wait time in milliseconds

    Returns:
        Dict with wait result

    Example:
        # Wait 2 seconds
        await internal_browser_wait(time_ms=2000)

        # Wait for element
        await internal_browser_wait(selector="#results")

        # Wait for loading to finish
        await internal_browser_wait(text_gone="Loading...")

        # Wait for navigation
        await internal_browser_wait(url_pattern="**/dashboard")
    """
    try:
        session, page = await _get_session_and_page(session_id, page_id)
        timeout = normalize_timeout(timeout_ms, 20000)

        waited_for = []

        if time_ms:
            await page.wait_for_timeout(time_ms)
            waited_for.append(f"delay:{time_ms}ms")

        if selector:
            await page.locator(selector).first.wait_for(state="visible", timeout=timeout)
            waited_for.append(f"selector:{selector}")

        if text:
            await page.get_by_text(text).first.wait_for(state="visible", timeout=timeout)
            waited_for.append(f"text:{text}")

        if text_gone:
            await page.get_by_text(text_gone).first.wait_for(state="hidden", timeout=timeout)
            waited_for.append(f"text_gone:{text_gone}")

        if url_pattern:
            await page.wait_for_url(url_pattern, timeout=timeout)
            waited_for.append(f"url:{url_pattern}")

        if load_state:
            await page.wait_for_load_state(load_state, timeout=timeout)
            waited_for.append(f"load_state:{load_state}")

        return {
            "success": True,
            "action": "wait",
            "waited_for": waited_for,
            "url": page.url,
            "session_id": session_id,
        }

    except PlaywrightTimeout:
        return {"success": False, "error": "Wait timeout exceeded"}
    except Exception as e:
        logger.error(f"Wait error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# SCREENSHOT
# =============================================================================


async def internal_browser_screenshot(
    session_id: str = "default",
    page_id: str | None = None,
    ref: str | None = None,
    full_page: bool = False,
    image_type: Literal["png", "jpeg"] = "png",
    quality: int | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Take a screenshot of the page or a specific element.

    Screenshots are saved to S3 storage and return a presigned URL.
    S3 storage must be configured - no base64 fallback.

    Args:
        session_id: Browser session ID
        page_id: Specific page/tab ID
        ref: Element reference to screenshot (optional, screenshots element only)
        full_page: Capture full scrollable page (default: False, viewport only)
        image_type: Image format - "png" or "jpeg"
        quality: JPEG quality 0-100 (only for jpeg)

    Returns:
        Dict with screenshot URL from S3

    Example:
        # Viewport screenshot
        result = await internal_browser_screenshot()

        # Full page screenshot
        result = await internal_browser_screenshot(full_page=True)

        # Element screenshot
        result = await internal_browser_screenshot(ref="e5")
    """
    from datetime import UTC, datetime
    from urllib.parse import urlparse
    from uuid import uuid4

    try:
        session, page = await _get_session_and_page(session_id, page_id)
        state = session.get_page_state(page)

        screenshot_opts = {"type": image_type}
        if image_type == "jpeg" and quality:
            screenshot_opts["quality"] = quality

        if ref:
            locator = _resolve_locator(page, ref, state)
            screenshot_bytes = await locator.screenshot(**screenshot_opts)
        else:
            screenshot_opts["full_page"] = full_page
            screenshot_bytes = await page.screenshot(**screenshot_opts)

        # Get runtime_context from config if not directly provided
        if not runtime_context and config:
            runtime_context = config.get("_runtime_context")

        # Upload to S3 storage (required)
        try:
            from src.services.storage.s3_storage import get_s3_storage

            s3_storage = get_s3_storage()
        except Exception as e:
            logger.error(f"S3 storage not available: {e}")
            return {
                "success": False,
                "error": "S3 storage is not configured. Screenshots require S3 storage to be available.",
            }

        # Get tenant info
        tenant_id = getattr(runtime_context, "tenant_id", None) if runtime_context else None
        agent_id = getattr(runtime_context, "agent_id", None) if runtime_context else None

        if not tenant_id:
            return {
                "success": False,
                "error": "Cannot save screenshot: tenant_id not available in runtime context.",
            }

        # Generate unique filename
        timestamp = datetime.now(UTC)
        date_path = timestamp.strftime("%Y/%m/%d")
        parsed_url = urlparse(page.url)
        domain = parsed_url.netloc.replace(".", "_").replace(":", "_")
        file_id = str(uuid4())[:8]
        ext = "jpg" if image_type == "jpeg" else "png"
        filename = f"screenshot_{domain}_{file_id}.{ext}"
        s3_key = f"tenants/{tenant_id}/screenshots/{date_path}/{filename}"

        # Upload to S3
        try:
            content_type = "image/jpeg" if image_type == "jpeg" else "image/png"
            s3_storage.upload_file(
                file_content=screenshot_bytes,
                key=s3_key,
                content_type=content_type,
                metadata={
                    "tenant_id": str(tenant_id),
                    "agent_id": str(agent_id) if agent_id else "",
                    "source_url": page.url,
                    "full_page": str(full_page),
                    "session_id": session_id,
                },
            )

            # Generate presigned URL (valid for 7 days)
            image_url = s3_storage.generate_presigned_url(s3_key, expiration=604800)
            logger.info(f"Screenshot saved to S3: {s3_key}")

        except Exception as e:
            logger.error(f"Failed to upload screenshot to S3: {e}")
            return {
                "success": False,
                "error": f"Failed to upload screenshot to S3: {e}",
            }

        return {
            "success": True,
            "image_url": image_url,
            "format": image_type,
            "full_page": full_page if not ref else False,
            "element_ref": ref,
            "page_url": page.url,
            "session_id": session_id,
            "message": f"Screenshot captured. IMPORTANT: Share this EXACT URL with the user (do not modify it): {image_url}",
        }

    except Exception as e:
        logger.error(f"Screenshot error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# COOKIES
# =============================================================================


async def internal_browser_get_cookies(
    session_id: str = "default",
    page_id: str | None = None,
    urls: list[str] | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Get cookies from the browser context.

    Args:
        session_id: Browser session ID
        page_id: Specific page/tab ID
        urls: Filter cookies by URLs (optional)

    Returns:
        Dict with list of cookies

    Example:
        result = await internal_browser_get_cookies()
    """
    try:
        session, page = await _get_session_and_page(session_id, page_id)

        if urls:
            cookies = await session.context.cookies(urls)
        else:
            cookies = await session.context.cookies()

        return {
            "success": True,
            "cookies": cookies,
            "count": len(cookies),
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Get cookies error: {e}")
        return {"success": False, "error": str(e)}


async def internal_browser_set_cookies(
    cookies: list[dict[str, Any]],
    session_id: str = "default",
    page_id: str | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Set cookies in the browser context.

    Args:
        cookies: List of cookie objects with:
            - name: Cookie name (required)
            - value: Cookie value (required)
            - url or domain+path: Cookie scope
            - expires: Expiry timestamp
            - httpOnly, secure, sameSite: Cookie flags
        session_id: Browser session ID
        page_id: Specific page/tab ID

    Returns:
        Dict with result

    Example:
        await internal_browser_set_cookies(cookies=[
            {"name": "session", "value": "abc123", "url": "https://example.com"}
        ])
    """
    try:
        session, _ = await _get_session_and_page(session_id, page_id)

        await session.context.add_cookies(cookies)

        return {
            "success": True,
            "cookies_set": len(cookies),
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Set cookies error: {e}")
        return {"success": False, "error": str(e)}


async def internal_browser_clear_cookies(
    session_id: str = "default",
    page_id: str | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Clear all cookies from the browser context.

    Args:
        session_id: Browser session ID
        page_id: Specific page/tab ID

    Returns:
        Dict with result

    Example:
        await internal_browser_clear_cookies()
    """
    try:
        session, _ = await _get_session_and_page(session_id, page_id)

        await session.context.clear_cookies()

        return {
            "success": True,
            "message": "All cookies cleared",
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Clear cookies error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# SESSION MANAGEMENT
# =============================================================================


async def internal_browser_new_page(
    session_id: str = "default",
    url: str | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Open a new browser tab/page.

    Args:
        session_id: Browser session ID
        url: URL to navigate to (optional)

    Returns:
        Dict with new page info

    Example:
        result = await internal_browser_new_page(url="https://example.com")
    """
    try:
        session = await BrowserSession.get_or_create(session_id)
        page_id, page = await session.new_page()

        if url:
            await page.goto(url)

        return {
            "success": True,
            "page_id": page_id,
            "url": page.url,
            "title": await page.title() if url else "",
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"New page error: {e}")
        return {"success": False, "error": str(e)}


async def internal_browser_close_page(
    page_id: str,
    session_id: str = "default",
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Close a browser tab/page.

    Args:
        page_id: Page ID to close
        session_id: Browser session ID

    Returns:
        Dict with result

    Example:
        await internal_browser_close_page(page_id="page_2")
    """
    try:
        session = await BrowserSession.get_or_create(session_id)
        await session.close_page(page_id)

        return {
            "success": True,
            "closed_page_id": page_id,
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Close page error: {e}")
        return {"success": False, "error": str(e)}


async def internal_browser_list_pages(
    session_id: str = "default",
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    List all open browser tabs/pages.

    Args:
        session_id: Browser session ID

    Returns:
        Dict with list of pages

    Example:
        result = await internal_browser_list_pages()
    """
    try:
        session = await BrowserSession.get_or_create(session_id)
        pages = await session.list_pages()

        return {
            "success": True,
            "pages": pages,
            "count": len(pages),
            "current_page_id": session.current_page_id,
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"List pages error: {e}")
        return {"success": False, "error": str(e)}


async def internal_browser_list_frames(
    session_id: str = "default",
    page_id: str | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    List all frames/iframes on the current page.

    Returns index, url, and name for each frame so you can target them
    using frame_selector in snapshot/fill/click/type.

    Args:
        session_id: Browser session ID
        page_id: Specific page/tab ID

    Returns:
        Dict with list of frames including index, url, name

    Example:
        result = await internal_browser_list_frames()
        # Returns:
        # {"frames": [{"index": 0, "url": "about:blank", "name": ""},
        #              {"index": 1, "url": "https://auth.magic.link/...", "name": ""}]}
        # Then use: snapshot(frame_selector="iframe[src*='magic.link']")
    """
    try:
        session, page = await _get_session_and_page(session_id, page_id)
        frames = []
        for i, frame in enumerate(page.frames):
            frames.append({"index": i, "url": frame.url, "name": frame.name})
        return {"success": True, "frames": frames, "count": len(frames), "session_id": session_id}
    except Exception as e:
        logger.error(f"List frames error: {e}")
        return {"success": False, "error": str(e)}


async def internal_browser_wait_for_new_page(
    session_id: str = "default",
    timeout_ms: int = 15000,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Wait for a new browser tab or popup to open and return its page_id.

    Use after triggering an action that opens a popup (e.g., Magic.link email
    submission, OAuth consent). The new page is auto-registered and can be
    interacted with using the returned page_id.

    Args:
        session_id: Browser session ID
        timeout_ms: Maximum time to wait in milliseconds (default: 15000)

    Returns:
        Dict with new_page_id, url, and title of the opened page

    Example:
        # Submit email form that opens a popup
        await internal_browser_click(ref="button:Send Magic Link")
        result = await internal_browser_wait_for_new_page(timeout_ms=15000)
        # {"success": True, "new_page_id": "popup_1", "url": "https://auth.magic.link/..."}
        # Then interact with popup:
        await internal_browser_snapshot(page_id=result["new_page_id"])
    """
    try:
        session = await BrowserSession.get_or_create(session_id)
        existing_ids = set(session.pages.keys())
        new_page_id = await session.wait_for_new_page(existing_ids, timeout_ms=timeout_ms)
        if not new_page_id:
            return {"success": False, "error": f"No popup/new page appeared within {timeout_ms}ms"}
        page = session.pages[new_page_id]
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        return {
            "success": True,
            "new_page_id": new_page_id,
            "url": page.url,
            "title": await page.title(),
            "session_id": session_id,
        }
    except Exception as e:
        logger.error(f"Wait for new page error: {e}")
        return {"success": False, "error": str(e)}


async def internal_browser_close_session(
    session_id: str = "default",
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Close browser session and all its pages.

    Args:
        session_id: Browser session ID to close

    Returns:
        Dict with result

    Example:
        await internal_browser_close_session(session_id="default")
    """
    try:
        await BrowserSession.close_session(session_id)

        return {
            "success": True,
            "message": f"Session '{session_id}' closed",
        }

    except Exception as e:
        logger.error(f"Close session error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# PAGE INFO
# =============================================================================


async def internal_browser_get_console(
    session_id: str = "default",
    page_id: str | None = None,
    limit: int = 50,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Get console messages from the page.

    Args:
        session_id: Browser session ID
        page_id: Specific page/tab ID
        limit: Maximum messages to return

    Returns:
        Dict with console messages

    Example:
        result = await internal_browser_get_console(limit=20)
    """
    try:
        session, page = await _get_session_and_page(session_id, page_id)
        state = session.get_page_state(page)

        messages = state.console[-limit:] if limit else state.console

        return {
            "success": True,
            "messages": [{"type": m.type, "text": m.text, "timestamp": m.timestamp} for m in messages],
            "count": len(messages),
            "total": len(state.console),
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Get console error: {e}")
        return {"success": False, "error": str(e)}


async def internal_browser_get_errors(
    session_id: str = "default",
    page_id: str | None = None,
    limit: int = 20,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Get page errors.

    Args:
        session_id: Browser session ID
        page_id: Specific page/tab ID
        limit: Maximum errors to return

    Returns:
        Dict with page errors

    Example:
        result = await internal_browser_get_errors()
    """
    try:
        session, page = await _get_session_and_page(session_id, page_id)
        state = session.get_page_state(page)

        errors = state.errors[-limit:] if limit else state.errors

        return {
            "success": True,
            "errors": [{"message": e.message, "name": e.name, "timestamp": e.timestamp} for e in errors],
            "count": len(errors),
            "total": len(state.errors),
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Get errors error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# ADDITIONAL ACTIONS (hover, scroll, drag, dialog, etc.)
# =============================================================================


async def internal_browser_hover(
    ref: str,
    session_id: str = "default",
    page_id: str | None = None,
    timeout_ms: int | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Hover over an element on the page.

    Args:
        ref: Element reference (snapshot ref, role:name, or CSS selector)
        session_id: Browser session ID
        page_id: Specific page/tab ID
        timeout_ms: Timeout in milliseconds

    Returns:
        Dict with hover result

    Example:
        await internal_browser_hover(ref="e1")
        await internal_browser_hover(ref="link:Profile")
    """
    try:
        session, page = await _get_session_and_page(session_id, page_id)
        state = session.get_page_state(page)
        timeout = normalize_timeout(timeout_ms)

        locator = _resolve_locator(page, ref, state)
        await locator.hover(timeout=timeout)

        return {
            "success": True,
            "action": "hover",
            "ref": ref,
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Hover error: {e}")
        return {"success": False, "error": to_ai_friendly_error(e, ref)}


async def internal_browser_scroll_into_view(
    ref: str,
    session_id: str = "default",
    page_id: str | None = None,
    timeout_ms: int | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Scroll an element into view.

    Args:
        ref: Element reference (snapshot ref, role:name, or CSS selector)
        session_id: Browser session ID
        page_id: Specific page/tab ID
        timeout_ms: Timeout in milliseconds

    Returns:
        Dict with scroll result

    Example:
        await internal_browser_scroll_into_view(ref="e15")
    """
    try:
        session, page = await _get_session_and_page(session_id, page_id)
        state = session.get_page_state(page)
        timeout = normalize_timeout(timeout_ms)

        locator = _resolve_locator(page, ref, state)
        await locator.scroll_into_view_if_needed(timeout=timeout)

        return {
            "success": True,
            "action": "scroll_into_view",
            "ref": ref,
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Scroll into view error: {e}")
        return {"success": False, "error": to_ai_friendly_error(e, ref)}


async def internal_browser_drag(
    source_ref: str,
    target_ref: str,
    session_id: str = "default",
    page_id: str | None = None,
    timeout_ms: int | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Drag an element and drop it onto another element.

    Args:
        source_ref: Element reference to drag from
        target_ref: Element reference to drop onto
        session_id: Browser session ID
        page_id: Specific page/tab ID
        timeout_ms: Timeout in milliseconds

    Returns:
        Dict with drag result

    Example:
        await internal_browser_drag(source_ref="e1", target_ref="e5")
    """
    try:
        session, page = await _get_session_and_page(session_id, page_id)
        state = session.get_page_state(page)
        timeout = normalize_timeout(timeout_ms)

        source_locator = _resolve_locator(page, source_ref, state)
        target_locator = _resolve_locator(page, target_ref, state)

        await source_locator.drag_to(target_locator, timeout=timeout)

        return {
            "success": True,
            "action": "drag",
            "source_ref": source_ref,
            "target_ref": target_ref,
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Drag error: {e}")
        return {"success": False, "error": str(e)}


async def internal_browser_handle_dialog(
    action: Literal["accept", "dismiss"] = "accept",
    prompt_text: str | None = None,
    session_id: str = "default",
    page_id: str | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Set up a handler for JavaScript dialogs (alert, confirm, prompt).

    IMPORTANT: Call this BEFORE the action that triggers the dialog.

    Args:
        action: "accept" to click OK/Yes, "dismiss" to click Cancel/No
        prompt_text: Text to enter if dialog is a prompt (optional)
        session_id: Browser session ID
        page_id: Specific page/tab ID

    Returns:
        Dict with result

    Example:
        # Set up handler before clicking button that shows dialog
        await internal_browser_handle_dialog(action="accept")
        await internal_browser_click(ref="e1")  # This triggers the dialog
    """
    try:
        session, page = await _get_session_and_page(session_id, page_id)

        async def dialog_handler(dialog):
            if action == "accept":
                if prompt_text is not None:
                    await dialog.accept(prompt_text)
                else:
                    await dialog.accept()
            else:
                await dialog.dismiss()

        # Set up one-time dialog handler
        page.once("dialog", dialog_handler)

        return {
            "success": True,
            "action": "handle_dialog",
            "dialog_action": action,
            "prompt_text": prompt_text,
            "message": f"Dialog handler set up. Next dialog will be {action}ed.",
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Handle dialog error: {e}")
        return {"success": False, "error": str(e)}


async def internal_browser_upload_file(
    file_ref: str,
    file_paths: list[str],
    session_id: str = "default",
    page_id: str | None = None,
    timeout_ms: int | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Upload file(s) to a file input element.

    Args:
        file_ref: Element reference for file input
        file_paths: List of file paths to upload
        session_id: Browser session ID
        page_id: Specific page/tab ID
        timeout_ms: Timeout in milliseconds

    Returns:
        Dict with upload result

    Example:
        await internal_browser_upload_file(
            file_ref="e5",
            file_paths=["/tmp/document.pdf"]
        )
    """
    try:
        session, page = await _get_session_and_page(session_id, page_id)
        state = session.get_page_state(page)
        timeout = normalize_timeout(timeout_ms)

        locator = _resolve_locator(page, file_ref, state)
        await locator.set_input_files(file_paths, timeout=timeout)

        return {
            "success": True,
            "action": "upload",
            "ref": file_ref,
            "files": file_paths,
            "count": len(file_paths),
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Upload file error: {e}")
        return {"success": False, "error": str(e)}


async def internal_browser_evaluate(
    expression: str,
    session_id: str = "default",
    page_id: str | None = None,
    ref: str | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Execute JavaScript code in the page context.

    Args:
        expression: JavaScript expression to evaluate. Can be a simple expression
                   or a function. If ref is provided, the function receives the element.
        session_id: Browser session ID
        page_id: Specific page/tab ID
        ref: Optional element reference - if provided, expression should be a
             function that receives the element: (el) => el.textContent

    Returns:
        Dict with evaluation result

    Example:
        # Get page title
        result = await internal_browser_evaluate(expression="document.title")

        # Get element text
        result = await internal_browser_evaluate(
            expression="(el) => el.textContent",
            ref="e5"
        )

        # Check if something is loaded
        result = await internal_browser_evaluate(
            expression="window.APP_LOADED === true"
        )
    """
    try:
        session, page = await _get_session_and_page(session_id, page_id)
        state = session.get_page_state(page)

        # Auto-wrap expressions with return statements in an IIFE
        # This handles cases where the agent writes code like:
        # const x = ...; return x;
        # instead of wrapping it in (() => { ... })()
        expr = expression.strip()
        if "return " in expr and not expr.startswith("(") and not expr.startswith("function"):
            expr = f"(() => {{ {expr} }})()"
            logger.debug(f"Auto-wrapped expression in IIFE: {expr[:100]}...")

        if ref:
            locator = _resolve_locator(page, ref, state)
            result = await locator.evaluate(expr)
        else:
            result = await page.evaluate(expr)

        return {
            "success": True,
            "action": "evaluate",
            "result": result,
            "ref": ref,
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Evaluate error: {e}")
        return {"success": False, "error": str(e)}


async def internal_browser_resize(
    width: int,
    height: int,
    session_id: str = "default",
    page_id: str | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Resize the browser viewport.

    Args:
        width: Viewport width in pixels
        height: Viewport height in pixels
        session_id: Browser session ID
        page_id: Specific page/tab ID

    Returns:
        Dict with resize result

    Example:
        # Desktop size
        await internal_browser_resize(width=1920, height=1080)

        # Mobile size
        await internal_browser_resize(width=375, height=812)
    """
    try:
        session, page = await _get_session_and_page(session_id, page_id)

        await page.set_viewport_size({"width": width, "height": height})

        return {
            "success": True,
            "action": "resize",
            "viewport": {"width": width, "height": height},
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Resize error: {e}")
        return {"success": False, "error": str(e)}


async def internal_browser_pdf(
    session_id: str = "default",
    page_id: str | None = None,
    path: str | None = None,
    format: str = "Letter",
    print_background: bool = True,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Generate a PDF of the current page.

    Note: PDF generation only works in headless mode.
    IMPORTANT: If saving to file, path must be within the workspace directory.

    Args:
        session_id: Browser session ID
        page_id: Specific page/tab ID
        path: Optional file path to save PDF (must be within workspace directory)
        format: Page format - "Letter", "A4", "Legal", etc.
        print_background: Include background graphics

    Returns:
        Dict with PDF result (path or base64 data)

    Example:
        result = await internal_browser_pdf(path="workspace/page.pdf")
    """
    import base64
    import uuid

    try:
        workspace_path = _get_workspace_path(config)

        # Validate or generate path within workspace
        if path:
            is_valid, error = _validate_path_in_workspace(path, workspace_path)
            if not is_valid:
                return {"success": False, "error": error}

        session, page = await _get_session_and_page(session_id, page_id)

        pdf_bytes = await page.pdf(
            format=format,
            print_background=print_background,
        )

        if path:
            # Ensure parent directory exists
            parent_dir = os.path.dirname(path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            with open(path, "wb") as f:
                f.write(pdf_bytes)
            return {
                "success": True,
                "action": "pdf",
                "path": path,
                "size_bytes": len(pdf_bytes),
                "session_id": session_id,
            }
        else:
            pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
            return {
                "success": True,
                "action": "pdf",
                "pdf_base64": pdf_base64,
                "size_bytes": len(pdf_bytes),
                "session_id": session_id,
            }

    except Exception as e:
        logger.error(f"PDF error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# STORAGE (localStorage / sessionStorage)
# =============================================================================


async def internal_browser_get_storage(
    storage_type: Literal["local", "session"] = "local",
    key: str | None = None,
    session_id: str = "default",
    page_id: str | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Get values from localStorage or sessionStorage.

    Args:
        storage_type: "local" for localStorage, "session" for sessionStorage
        key: Specific key to get (if None, returns all storage)
        session_id: Browser session ID
        page_id: Specific page/tab ID

    Returns:
        Dict with storage data

    Example:
        # Get all localStorage
        result = await internal_browser_get_storage(storage_type="local")

        # Get specific key
        result = await internal_browser_get_storage(
            storage_type="local",
            key="authToken"
        )
    """
    try:
        session, page = await _get_session_and_page(session_id, page_id)

        storage_obj = "localStorage" if storage_type == "local" else "sessionStorage"

        if key:
            result = await page.evaluate(f"{storage_obj}.getItem({json.dumps(key)})")
            return {
                "success": True,
                "storage_type": storage_type,
                "key": key,
                "value": result,
                "session_id": session_id,
            }
        else:
            result = await page.evaluate(
                f"""
                (() => {{
                    const storage = {storage_obj};
                    const data = {{}};
                    for (let i = 0; i < storage.length; i++) {{
                        const key = storage.key(i);
                        data[key] = storage.getItem(key);
                    }}
                    return data;
                }})()
            """
            )
            return {
                "success": True,
                "storage_type": storage_type,
                "data": result,
                "count": len(result) if result else 0,
                "session_id": session_id,
            }

    except Exception as e:
        logger.error(f"Get storage error: {e}")
        return {"success": False, "error": str(e)}


async def internal_browser_set_storage(
    key: str,
    value: str,
    storage_type: Literal["local", "session"] = "local",
    session_id: str = "default",
    page_id: str | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Set a value in localStorage or sessionStorage.

    Args:
        key: Storage key
        value: Value to store
        storage_type: "local" for localStorage, "session" for sessionStorage
        session_id: Browser session ID
        page_id: Specific page/tab ID

    Returns:
        Dict with result

    Example:
        await internal_browser_set_storage(
            key="theme",
            value="dark",
            storage_type="local"
        )
    """
    try:
        session, page = await _get_session_and_page(session_id, page_id)

        storage_obj = "localStorage" if storage_type == "local" else "sessionStorage"

        await page.evaluate(f"{storage_obj}.setItem({json.dumps(key)}, {json.dumps(value)})")

        return {
            "success": True,
            "storage_type": storage_type,
            "key": key,
            "value": value,
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Set storage error: {e}")
        return {"success": False, "error": str(e)}


async def internal_browser_clear_storage(
    storage_type: Literal["local", "session"] = "local",
    session_id: str = "default",
    page_id: str | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Clear localStorage or sessionStorage.

    Args:
        storage_type: "local" for localStorage, "session" for sessionStorage
        session_id: Browser session ID
        page_id: Specific page/tab ID

    Returns:
        Dict with result

    Example:
        await internal_browser_clear_storage(storage_type="local")
    """
    try:
        session, page = await _get_session_and_page(session_id, page_id)

        storage_obj = "localStorage" if storage_type == "local" else "sessionStorage"

        await page.evaluate(f"{storage_obj}.clear()")

        return {
            "success": True,
            "storage_type": storage_type,
            "message": f"{storage_type}Storage cleared",
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Clear storage error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# NETWORK SETTINGS
# =============================================================================


async def internal_browser_set_offline(
    offline: bool = True,
    session_id: str = "default",
    page_id: str | None = None,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Set browser offline/online mode.

    Args:
        offline: True to go offline, False to go online
        session_id: Browser session ID
        page_id: Specific page/tab ID

    Returns:
        Dict with result

    Example:
        # Go offline
        await internal_browser_set_offline(offline=True)

        # Go back online
        await internal_browser_set_offline(offline=False)
    """
    try:
        session = await BrowserSession.get_or_create(session_id)

        if not session.context:
            return {"success": False, "error": "No browser context available"}

        await session.context.set_offline(offline)

        return {
            "success": True,
            "offline": offline,
            "message": f"Browser is now {'offline' if offline else 'online'}",
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Set offline error: {e}")
        return {"success": False, "error": str(e)}


async def internal_browser_set_extra_headers(
    headers: dict[str, str],
    session_id: str = "default",
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Set extra HTTP headers that will be sent with every request.

    Args:
        headers: Dictionary of header name -> value
        session_id: Browser session ID

    Returns:
        Dict with result

    Example:
        await internal_browser_set_extra_headers(
            headers={
                "X-Custom-Header": "value",
                "Authorization": "Bearer token123"
            }
        )
    """
    try:
        session = await BrowserSession.get_or_create(session_id)

        if not session.context:
            return {"success": False, "error": "No browser context available"}

        await session.context.set_extra_http_headers(headers)

        return {
            "success": True,
            "headers": headers,
            "count": len(headers),
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Set extra headers error: {e}")
        return {"success": False, "error": str(e)}


async def internal_browser_set_http_credentials(
    username: str | None = None,
    password: str | None = None,
    session_id: str = "default",
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Set HTTP Basic Auth credentials for the browser session.

    Note: This recreates the browser context with the new credentials.
    Open pages will be restored but may lose some state.

    Args:
        username: Username for HTTP Basic Auth (None to clear)
        password: Password for HTTP Basic Auth (None to clear)
        session_id: Browser session ID

    Returns:
        Dict with result

    Example:
        # Set credentials
        await internal_browser_set_http_credentials(
            username="admin",
            password="secret"
        )

        # Clear credentials
        await internal_browser_set_http_credentials()
    """
    try:
        session = await BrowserSession.get_or_create(session_id)

        if not session.browser:
            return {"success": False, "error": "No browser available"}

        # Save current pages' URLs to restore them
        page_urls = []
        for page_id, page in session.pages.items():
            try:
                page_urls.append((page_id, page.url))
            except Exception:
                pass

        # Close existing context
        if session.context:
            try:
                await session.context.close()
            except Exception:
                pass

        # Create new context with credentials
        http_credentials = None
        if username and password:
            http_credentials = {"username": username, "password": password}

        session.context = await session.browser.new_context(
            http_credentials=http_credentials,
            viewport={"width": 1280, "height": 720},
        )

        # Clear old pages
        session.pages = {}
        session.current_page_id = None
        session._page_state_store = {}

        # Restore pages using session's new_page method
        for page_id, url in page_urls:
            try:
                _, page = await session.new_page(page_id=page_id)
                if url and url != "about:blank":
                    await page.goto(url, wait_until="load", timeout=30000)
            except Exception:
                pass

        if username and password:
            return {
                "success": True,
                "credentials_set": True,
                "username": username,
                "pages_restored": len(page_urls),
                "session_id": session_id,
            }
        else:
            return {
                "success": True,
                "credentials_set": False,
                "message": "HTTP credentials cleared",
                "pages_restored": len(page_urls),
                "session_id": session_id,
            }

    except Exception as e:
        logger.error(f"Set HTTP credentials error: {e}")
        return {"success": False, "error": str(e)}


async def internal_browser_focus_page(
    page_id: str,
    session_id: str = "default",
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Focus/switch to a specific browser page/tab.

    Args:
        page_id: Page ID to focus
        session_id: Browser session ID

    Returns:
        Dict with result

    Example:
        await internal_browser_focus_page(page_id="page_2")
    """
    try:
        session = await BrowserSession.get_or_create(session_id)

        if page_id not in session.pages:
            return {
                "success": False,
                "error": f"Page '{page_id}' not found. Use internal_browser_list_pages to see available pages.",
            }

        page = session.pages[page_id]
        session.current_page_id = page_id
        await page.bring_to_front()

        return {
            "success": True,
            "action": "focus",
            "page_id": page_id,
            "url": page.url,
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Focus page error: {e}")
        return {"success": False, "error": str(e)}


async def internal_browser_get_network_requests(
    session_id: str = "default",
    page_id: str | None = None,
    filter_pattern: str | None = None,
    limit: int = 50,
    runtime_context: Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Get recorded network requests from the page.

    Args:
        session_id: Browser session ID
        page_id: Specific page/tab ID
        filter_pattern: Filter requests by URL pattern (substring match)
        limit: Maximum requests to return

    Returns:
        Dict with network requests

    Example:
        # Get all requests
        result = await internal_browser_get_network_requests()

        # Filter by pattern
        result = await internal_browser_get_network_requests(filter_pattern="api")
    """
    try:
        session, page = await _get_session_and_page(session_id, page_id)
        state = session.get_page_state(page)

        requests = state.requests
        if filter_pattern:
            requests = [r for r in requests if filter_pattern in r.url]

        requests = requests[-limit:] if limit else requests

        return {
            "success": True,
            "requests": [
                {
                    "id": r.id,
                    "timestamp": r.timestamp,
                    "method": r.method,
                    "url": r.url,
                    "resource_type": r.resource_type,
                    "status": r.status,
                    "ok": r.ok,
                }
                for r in requests
            ],
            "count": len(requests),
            "total": len(state.requests),
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Get network requests error: {e}")
        return {"success": False, "error": str(e)}
