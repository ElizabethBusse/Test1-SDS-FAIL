# import streamlit as st
import asyncio
from playwright.async_api import async_playwright

# st.write("Starting the test…")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://annas-archive.org/")
        title = await page.title()
        # st.write(title)
        await browser.close()
        return title

if __name__ == '__main__':
    loop = asyncio.SelectorEventLoop()
    asyncio.set_event_loop(loop)
    title=loop.run_until_complete(main())
    print(title)