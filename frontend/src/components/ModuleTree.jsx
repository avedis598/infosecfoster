import React, { useState, useEffect } from 'react'

export default function ModuleTree({ modulesHierarchy, selectedSteps, setSelectedSteps, stepStatus = {} }) {
  const [expanded, setExpanded] = useState({})

  const getStatus = (stepId) => {
    if (!stepStatus) return undefined;
    if (stepStatus[stepId]) return stepStatus[stepId];
    const parts = stepId.split('.');
    let curr = stepStatus;
    for (let p of parts) {
      if (curr && curr[p]) curr = curr[p];
      else return undefined;
    }
    return curr;
  }


  // Toggle expanding a module or step
  const toggleExpand = (id) => {
    setExpanded(prev => ({ ...prev, [id]: !prev[id] }))
  }

  // Handle checking a module (selects all steps inside)
  const handleModuleCheck = (mod, isChecked) => {
    const stepIds = mod.steps.map(s => s.id)
    if (isChecked) {
      setSelectedSteps(prev => [...new Set([...prev, ...stepIds])])
    } else {
      setSelectedSteps(prev => prev.filter(id => !stepIds.includes(id)))
    }
  }

  // Handle checking a specific step
  const handleStepCheck = (stepId, isChecked) => {
    if (isChecked) {
      setSelectedSteps(prev => [...prev, stepId])
    } else {
      setSelectedSteps(prev => prev.filter(id => id !== stepId))
    }
  }

  const selectAll = () => {
    const all = []
    modulesHierarchy.forEach(m => m.steps.forEach(s => all.push(s.id)))
    setSelectedSteps(all)
  }

  return (
    <div className="flex flex-col h-full bg-obsidian rounded-[12px] border border-white/5 overflow-hidden font-mono text-[13px] text-gray-300">
      <div className="p-3 border-b border-white/5 flex justify-between items-center bg-white/[0.02]">
        <span className="font-bold tracking-wide text-white">Execution Modules</span>
        <div className="flex gap-2">
          <button onClick={selectAll} className="px-2 py-1 bg-white/10 hover:bg-white/20 rounded text-xs transition-colors">All</button>
          <button onClick={() => setSelectedSteps([])} className="px-2 py-1 bg-white/10 hover:bg-white/20 rounded text-xs transition-colors">None</button>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto p-2">
        {modulesHierarchy.map(mod => {
          const modStepIds = mod.steps.map(s => s.id)
          const selectedCount = modStepIds.filter(id => selectedSteps.includes(id)).length
          const isAllSelected = selectedCount === modStepIds.length && modStepIds.length > 0
          const isIndeterminate = selectedCount > 0 && selectedCount < modStepIds.length
          const isExpanded = expanded[mod.id]

          return (
            <div key={mod.id} className="mb-1">
              <div className="flex items-center gap-2 hover:bg-white/[0.03] p-1.5 rounded cursor-pointer group">
                <button 
                  onClick={() => toggleExpand(mod.id)} 
                  className="w-4 h-4 text-emerald-500 font-bold opacity-70 hover:opacity-100 flex items-center justify-center transition-all"
                >
                  {isExpanded ? '[-]' : '[+]'}
                </button>
                <input 
                  type="checkbox" 
                  className="accent-emerald-500 cursor-pointer"
                  checked={isAllSelected}
                  ref={el => { if(el) el.indeterminate = isIndeterminate }}
                  onChange={(e) => handleModuleCheck(mod, e.target.checked)}
                />
                <div className="flex flex-1 items-center justify-between" onClick={() => toggleExpand(mod.id)}>
                  <span className={`font-bold transition-colors ${isAllSelected || isIndeterminate ? 'text-emerald-500' : 'text-gray-400 group-hover:text-gray-300'}`}>
                    {mod.name}
                  </span>
                  {(() => {
                    const statuses = mod.steps.map(s => getStatus(s.id));
                    if (statuses.includes('running')) {
                      return <span className="ml-2 text-[10px] font-bold px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-400 border border-sky-500/30 animate-pulse">RUNNING</span>;
                    }
                    if (statuses.includes('failed')) {
                      return <span className="ml-2 text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30">FAILED</span>;
                    }
                    if (statuses.includes('need_rerun')) {
                      return <span className="ml-2 text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">NEED RERUN</span>;
                    }
                    // Only show success if ALL steps in the module are success
                    if (statuses.length > 0 && statuses.every(s => s === 'success')) {
                      return <span className="ml-2 text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">SUCCESS</span>;
                    }
                    return null;
                  })()}
                </div>
              </div>

              {isExpanded && (
                <div className="ml-5 pl-2 border-l border-white/10 py-1 flex flex-col gap-1">
                  {mod.steps.map(step => {
                    const isStepSelected = selectedSteps.includes(step.id)
                    const isStepExpanded = expanded[step.id]
                    return (
                      <div key={step.id} className="flex flex-col">
                        <div className="flex items-start gap-2 hover:bg-white/[0.03] p-1 rounded cursor-pointer group">
                          <button 
                            onClick={() => toggleExpand(step.id)} 
                            className="w-4 h-4 text-emerald-500 font-bold opacity-70 hover:opacity-100 flex items-center justify-center transition-all mt-0.5"
                          >
                            {isStepExpanded ? '[-]' : '[+]'}
                          </button>
                          <input 
                            type="checkbox" 
                            className="accent-emerald-500 cursor-pointer mt-1"
                            checked={isStepSelected}
                            onChange={(e) => handleStepCheck(step.id, e.target.checked)}
                          />
                          <div className="flex flex-1 items-center justify-between" onClick={() => toggleExpand(step.id)}>
                            <span className={`transition-colors leading-tight ${isStepSelected ? 'text-white' : 'text-gray-400 group-hover:text-gray-300'}`}>
                              {step.title}
                            </span>
                            {getStatus(step.id) === 'success' && <span className="ml-2 text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">SUCCESS</span>}
                            {getStatus(step.id) === 'failed' && <span className="ml-2 text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30">FAILED</span>}
                            {getStatus(step.id) === 'running' && <span className="ml-2 text-[10px] font-bold px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-400 border border-sky-500/30 animate-pulse">RUNNING</span>}
                            {getStatus(step.id) === 'need_rerun' && <span className="ml-2 text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">NEED RERUN</span>}
                          </div>
                        </div>
                        
                        {isStepExpanded && (
                          <div className="ml-6 pl-2 border-l border-white/5 py-1 flex flex-col gap-1">
                            {step.cmds.map((cmd, idx) => (
                              <div key={idx} className="flex items-center gap-2 text-gray-500">
                                <div className="w-3 h-3 rounded-full border border-gray-600 flex-shrink-0" />
                                <span className="text-[12px]">{cmd.label}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
