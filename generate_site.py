import json

def convert():
    with open('docs/blueprint.md', 'r') as f:
        markdown_content = f.read()
    
    # Escape for JS template literal
    escaped_markdown = markdown_content.replace('`', '\\`').replace('$', '\\$')

    html_template = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SIH26190 - Secure DMS Blueprint</title>
    
    <!-- GitHub Markdown CSS for beautiful default styling -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.3.0/github-markdown-dark.min.css">
    
    <!-- Highlight.js for code block syntax highlighting -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/styles/github-dark.min.css">
    
    <style>
        body {{
            background-color: #0d1117;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
        }}
        .container {{
            max-width: 1012px;
            margin: 0 auto;
            padding: 40px;
        }}
        .markdown-body {{
            box-sizing: border-box;
            min-width: 200px;
            max-width: 980px;
            margin: 0 auto;
            padding: 45px;
            background-color: #0d1117;
            border: 1px solid #30363d;
            border-radius: 6px;
        }}
        @media (max-width: 767px) {{
            .markdown-body {{
                padding: 15px;
            }}
            .container {{
                padding: 10px;
            }}
        }}
        /* Fix for markdown body code background */
        .markdown-body pre {{
            background-color: #161b22;
        }}
    </style>
</head>
<body>
    <div class="container">
        <article class="markdown-body" id="content">
            Loading blueprint...
        </article>
    </div>

    <!-- Marked.js for markdown parsing -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <!-- Highlight.js -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/highlight.min.js"></script>
    
    <script>
        const markdown = `{escaped_markdown}`;
        
        // Configure marked to use highlight.js
        marked.setOptions({{
            highlight: function(code, lang) {{
                const language = hljs.getLanguage(lang) ? lang : 'plaintext';
                return hljs.highlight(code, {{ language }}).value;
            }},
            gfm: true,
            breaks: true
        }});
        
        // Parse and render
        document.getElementById('content').innerHTML = marked.parse(markdown);
    </script>
</body>
</html>"""

    with open('website/index.html', 'w') as f:
        f.write(html_template)

if __name__ == '__main__':
    convert()
