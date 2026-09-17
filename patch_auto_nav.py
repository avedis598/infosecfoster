import re

with open("frontend/src/components/Dashboard.jsx", "r") as f:
    c = f.read()

inject_point = r"""  const \[selectedSteps, setSelectedSteps\] = useState\(\[\]\)
  const \[modulesHierarchy, setModulesHierarchy\] = useState\(\[\]\)"""

new_code = """  const [selectedSteps, setSelectedSteps] = useState([])
  const [modulesHierarchy, setModulesHierarchy] = useState([])
  const [hasAutoNavigated, setHasAutoNavigated] = useState(false)

  // Auto-navigate to Overview if all modules are SUCCESS
  useEffect(() => {
    if (modulesHierarchy.length === 0 || !client || !client.step_status || hasAutoNavigated) return;
    
    let allSuccess = true;
    let hasSteps = false;

    for (const mod of modulesHierarchy) {
      for (const step of mod.steps) {
        hasSteps = true;
        const parts = step.id.split('.');
        let curr = client.step_status;
        for (const p of parts) {
          if (curr && curr[p]) curr = curr[p];
          else { curr = undefined; break; }
        }
        if (curr !== 'success') {
          allSuccess = false;
          break;
        }
      }
      if (!allSuccess) break;
    }

    if (hasSteps && allSuccess) {
      setActiveTab('Overview');
      setHasAutoNavigated(true);
    }
  }, [client?.step_status, modulesHierarchy, hasAutoNavigated]);"""

c = re.sub(inject_point, new_code, c)

with open("frontend/src/components/Dashboard.jsx", "w") as f:
    f.write(c)
