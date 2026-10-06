package com.robutpit.pitbrowser

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/** Те же случаи, что в desktop/test/omnibox.test.js. */
class OmniboxTest {
    @Test fun addresses() {
        assertEquals("https://example.com", Omnibox.toUrl("example.com"))
        assertEquals("https://sub.site.uz/path?a=1", Omnibox.toUrl("  sub.site.uz/path?a=1 "))
        assertEquals("https://a.b/c", Omnibox.toUrl("https://a.b/c"))
        assertEquals("http://localhost:3000", Omnibox.toUrl("localhost:3000"))
        assertEquals("http://192.168.1.1", Omnibox.toUrl("192.168.1.1"))
        assertEquals("https://сайт.рф", Omnibox.toUrl("сайт.рф"))
    }

    @Test fun search() {
        assertEquals(
            "https://www.google.com/search?q=%D0%BF%D0%BE%D0%B3%D0%BE%D0%B4%D0%B0%20%D1%82%D0%B0%D1%88%D0%BA%D0%B5%D0%BD%D1%82",
            Omnibox.toUrl("погода ташкент"),
        )
        assertEquals("https://duckduckgo.com/?q=hello", Omnibox.toUrl("hello", "duckduckgo"))
        assertEquals("https://www.google.com/search?q=node.js%20tutorial", Omnibox.toUrl("node.js tutorial"))
        assertEquals("https://www.bing.com/search?q=example.com", Omnibox.toUrl("?example.com", "bing"))
        assertEquals("https://www.google.com/search?q=version%201.2", Omnibox.toUrl("version 1.2"))
        assertEquals("https://www.google.com/search?q=3.14", Omnibox.toUrl("3.14"))
        assertNull(Omnibox.toUrl(""))
    }
}
