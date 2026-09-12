from datetime import date
from playwright.sync_api import sync_playwright
from report_queries import get_report_data


def build_html(data: dict) -> str:
    today = date.today().isoformat()

    top_5_rows = "".join(
        f"<tr><td>{b['title']}</td><td>£{b['price']:.2f}</td></tr>"
        for b in data["top_5_expensive"]
    )

    rating_rows = "".join(
        f"<tr><td>{r['rating']} star{'s' if r['rating'] != 1 else ''}</td><td>{r['count']}</td></tr>"
        for r in data["books_per_rating"]
    )

    all_books_rows = "".join(
        f"<tr><td>{b['title']}</td><td>£{b['price']:.2f}</td><td>{b['rating'] or '-'}</td></tr>"
        for b in data["all_books"]
    )

    return f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; color: #1a1a1a; }}
            h1 {{ font-size: 22px; margin-bottom: 4px; }}
            .date {{ color: #666; font-size: 12px; margin-bottom: 24px; }}
            .totals {{ display: flex; gap: 40px; margin-bottom: 24px; }}
            .total-box {{ border: 1px solid #ddd; border-radius: 6px; padding: 12px 20px; }}
            .total-box .label {{ font-size: 11px; color: #666; text-transform: uppercase; }}
            .total-box .value {{ font-size: 24px; font-weight: bold; }}
            h2 {{ font-size: 16px; margin-top: 32px; border-bottom: 2px solid #333; padding-bottom: 4px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
            thead {{ display: table-header-group; }}
            th {{ text-align: left; background: #f0f0f0; padding: 6px 8px; font-size: 12px; }}
            td {{ padding: 6px 8px; font-size: 12px; border-bottom: 1px solid #eee; }}
            /* The page-break fix: never let a single row be sliced across two pages */
            tr {{ break-inside: avoid; }}
        </style>
    </head>
    <body>
        <h1>Book Catalogue Report</h1>
        <div class="date">Generated on {today}</div>

        <div class="totals">
            <div class="total-box">
                <div class="label">Total Books</div>
                <div class="value">{data['total_books']}</div>
            </div>
            <div class="total-box">
                <div class="label">Average Price</div>
                <div class="value">£{data['average_price']:.2f}</div>
            </div>
        </div>

        <h2>Top 5 Most Expensive Books</h2>
        <table>
            <thead><tr><th>Title</th><th>Price</th></tr></thead>
            <tbody>{top_5_rows}</tbody>
        </table>

        <h2>Books by Rating</h2>
        <table>
            <thead><tr><th>Rating</th><th>Count</th></tr></thead>
            <tbody>{rating_rows}</tbody>
        </table>

        <h2>All Books ({data['total_books']})</h2>
        <table>
            <thead><tr><th>Title</th><th>Price</th><th>Rating</th></tr></thead>
            <tbody>{all_books_rows}</tbody>
        </table>
    </body>
    </html>
    """


def render_pdf(html: str, output_path: str):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        page.pdf(path=output_path, format="A4", print_background=True)
        browser.close()


if __name__ == "__main__":
    data = get_report_data()
    html = build_html(data)
    render_pdf(html, "reports/test.pdf")
    print("Rendered reports/test.pdf")