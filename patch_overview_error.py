import re

with open("frontend/src/components/Dashboard.jsx", "r") as f:
    c = f.read()

# I will update fetchOverview to handle error
old_fetch = """      const data = await res.json()
      if (data.status === 'success') setOverviewData(data)
    } catch (e) {"""

new_fetch = """      const data = await res.json()
      if (data.status === 'success') {
          setOverviewData(data)
      } else {
          setOverviewData({ error: data.message || "Unknown error" })
      }
    } catch (e) {"""

c = c.replace(old_fetch, new_fetch)

# Now, in the UI, if overviewData.error exists, display it!
old_ui = """              <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-6">Pod Status</h3>"""

new_ui = """              <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-6">Pod Status</h3>
              {overviewData && overviewData.error && (
                <div className="bg-red-500/20 text-red-400 border border-red-500/30 p-3 mb-4 rounded-lg text-xs font-mono">
                  Error Fetching Data: {overviewData.error}
                </div>
              )}"""

c = c.replace(old_ui, new_ui)

with open("frontend/src/components/Dashboard.jsx", "w") as f:
    f.write(c)
