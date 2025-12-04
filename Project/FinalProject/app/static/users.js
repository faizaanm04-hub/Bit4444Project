/**
 * FMZB Hub - Users Module JavaScript
 */

const E = (id) => document.getElementById(id);

async function loadDashboard() {
  try {
    await loadMetrics();
    await loadChart();
    await loadRecentUsers();
    setupChatHandler();
  } catch (error) {
    console.error('Dashboard error:', error);
  }
}

async function loadMetrics() {
  try {
    const res = await fetch('/users/api/metrics');
    const data = await res.json();
    if (E('kpiTotal')) E('kpiTotal').textContent = data.total;
    if (E('kpiActive')) E('kpiActive').textContent = data.active;
    if (E('kpiDisabled')) E('kpiDisabled').textContent = data.disabled;
  } catch (error) {
    console.error('Metrics error:', error);
  }
}

async function loadChart() {
  try {
    const res = await fetch('/users/api/charts/roles');
    const data = await res.json();
    
    const dataSource = {
      chart: {
        caption: 'Users by Role',
        yaxisname: 'Count',
        baseFontColor: '#F9F9F9',
        baseFontSize: '12',
        canvasBgColor: '#121212',
        showBorder: '0',
        plotBorderThickness: '0',
        plotFillAlpha: '85',
        showLegend: '1',
        showValues: '1',
        theme: 'fusion',
        paletteColors: '#E03E36,#4caf50'
      },
      categories: data.categories,
      dataset: data.dataset
    };
    
    const chart = new FusionCharts({
      type: 'column2d',
      renderAt: 'chartUsersByRole',
      width: '100%',
      height: '360',
      dataFormat: 'json',
      dataSource: dataSource
    });
    
    chart.render();
  } catch (error) {
    console.error('Chart error:', error);
  }
}

async function loadRecentUsers() {
  try {
    const res = await fetch('/users/api/recent-users');
    const users = await res.json();
    
    const tbody = E('recentUsersTable').querySelector('tbody');
    if (!users || users.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center text-secondary py-3">No users</td></tr>';
      return;
    }
    
    tbody.innerHTML = users.map(u => `
      <tr>
        <td><small>${u.Email}</small></td>
        <td>${u.ContactFirstName} ${u.ContactLastName}</td>
        <td><span class="badge ${u.UserType === 'merchant' ? 'bg-warning' : 'bg-info'}">${u.UserType}</span></td>
        <td><span class="badge ${u.Status === 'active' ? 'bg-success' : 'bg-danger'}">${u.Status}</span></td>
        <td><small>${new Date(u.TimeOfCreation).toLocaleDateString()}</small></td>
      </tr>
    `).join('');
  } catch (error) {
    console.error('Recent users error:', error);
  }
}

function setupChatHandler() {
  const askBtn = E('chatAskBtn');
  const prompt = E('chatPrompt');
  const result = E('chatResult');
  
  if (!askBtn) return;
  
  askBtn.addEventListener('click', async () => {
    const q = (prompt.value || '').trim();
    if (!q) {
      result.innerHTML = '<span class="text-warning">Enter a question</span>';
      return;
    }
    
    askBtn.disabled = true;
    askBtn.textContent = 'Analyzing…';
    
    try {
      const res = await fetch('/users/api/chat-analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q })
      });
      
      const data = await res.json();
      result.innerHTML = `<div class="mb-2"><strong style="color:var(--fmzb-red);">Q:</strong> ${q}</div><div class="text-secondary">${data.answer || 'No response'}</div>`;
    } catch (error) {
      result.innerHTML = `<span class="text-danger">Error: ${error.message}</span>`;
    } finally {
      askBtn.disabled = false;
      askBtn.textContent = 'Analyze';
    }
  });
  
  prompt.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') askBtn.click();
  });
}
