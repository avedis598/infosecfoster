import sys
with open("frontend/src/components/Dashboard.jsx", "r") as f:
    d = f.read()

# Add to handleUploadKey
old_alert = "alert(`${type.toUpperCase()} securely uploaded to Google Secret Manager!`)"
new_alert = """alert(`${type.toUpperCase()} securely uploaded to Google Secret Manager!`)
        if (type === 'cf') {
          localStorage.setItem('cf_token_common', input)
        }"""

d = d.replace(old_alert, new_alert)

with open("frontend/src/components/Dashboard.jsx", "w") as f:
    f.write(d)
