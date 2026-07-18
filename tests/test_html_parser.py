import pytest
from pipeline.parsers.html_parser import HTMLParser

def test_html_parser_basic_extraction():
    html_content = """
    <html>
        <head>
            <title>BLS Test Release</title>
            <meta name="DC.date" content="2026-07-18T08:30:00Z" />
        </head>
        <body>
            <h1>Consumer Price Index - June 2026</h1>
            <p>This is a short UI snippet.</p>
            <p>The Consumer Price Index for All Urban Consumers (CPI-U) increased 0.2 percent in June on a seasonally adjusted basis, the U.S. Bureau of Labor Statistics reported today. Over the last 12 months, the all items index increased 3.0 percent before seasonal adjustment.</p>
            <div id="bodytext">
                <p>This is the main body text.</p>
                <table>
                    <thead>
                        <tr><th>Category</th><th>Value</th></tr>
                    </thead>
                    <tbody>
                        <tr><td>Food</td><td>1.2</td></tr>
                        <tr><td>Energy</td><td>-0.5</td></tr>
                    </tbody>
                </table>
            </div>
            <img src="/charts/cpi_june2026.png" alt="CPI Chart" />
            <a href="/pdf/cpi_june2026.pdf">Download PDF</a>
        </body>
    </html>
    """
    
    metadata = {
        "uuid": "test-uuid-123",
        "source_url": "https://www.bls.gov/news.release/cpi.htm"
    }
    
    parser = HTMLParser()
    unified_obj = parser.parse(html_content, metadata)
    
    # Check Metadata
    assert unified_obj.metadata.uuid == "test-uuid-123"
    assert unified_obj.metadata.source_type == "HTML"
    
    # Check HTML Schema
    html = unified_obj.html
    assert html is not None
    assert html.page_url == "https://www.bls.gov/news.release/cpi.htm"
    assert html.page_title == "BLS Test Release"
    assert html.publication_datetime == "2026-07-18T08:30:00Z"
    assert html.headline == "Consumer Price Index - June 2026"
    assert "increased 0.2 percent in June" in html.summary
    assert "main body text" in html.main_content
    
    # Check Links
    assert "/pdf/cpi_june2026.pdf" in html.links
    
    # Check Tables
    assert len(html.tables) == 1
    table = html.tables[0]
    assert table["headers"] == ["Category", "Value"]
    assert len(table["rows"]) == 2
    assert table["rows"][0] == ["Food", "1.2"]
    
    # Check Charts
    assert len(html.charts) == 1
    assert html.charts[0]["src"] == "/charts/cpi_june2026.png"

def test_html_parser_fallback_extraction():
    html_content = """
    <html>
        <head>
            <title>Minimal BLS Page</title>
        </head>
        <body>
            <time datetime="2026-07-15T10:00:00Z"></time>
            <main>Just some text.</main>
        </body>
    </html>
    """
    parser = HTMLParser()
    unified_obj = parser.parse(html_content, {})
    html = unified_obj.html
    
    assert html.page_title == "Minimal BLS Page"
    assert html.publication_datetime == "2026-07-15T10:00:00Z"
    assert html.headline is None
    assert html.summary is None
    assert html.main_content == "Just some text."
    assert len(html.tables) == 0
    assert len(html.charts) == 0
