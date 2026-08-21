// AI Infrastructure Copilot — design tokens + sample data
window.THEMES = {
  dark: {
    name: 'dark',
    bg: '#0a0e13',
    bgSubtle: '#0d1219',
    sidebarBg: '#0d1219',
    surface: '#12181f',
    surfaceAlt: '#161d25',
    surfaceHover: '#1b232c',
    border: '#1f2831',
    borderStrong: '#2a3441',
    textPrimary: '#e8edf2',
    textSecondary: '#93a1ad',
    textTertiary: '#5f6b76',
    accent: '#4c8bf5',
    accentHover: '#3b78e0',
    accentSoft: 'rgba(76,139,245,0.14)',
    accentBorder: 'rgba(76,139,245,0.35)',
    green: '#3ecf8e', greenSoft: 'rgba(62,207,142,0.13)', greenBorder: 'rgba(62,207,142,0.3)',
    yellow: '#f0b429', yellowSoft: 'rgba(240,180,41,0.13)', yellowBorder: 'rgba(240,180,41,0.3)',
    red: '#f0554f', redSoft: 'rgba(240,85,79,0.13)', redBorder: 'rgba(240,85,79,0.32)',
    gray: '#6b7684', graySoft: 'rgba(107,118,132,0.15)', grayBorder: 'rgba(107,118,132,0.3)',
    orange: '#f5924a', orangeSoft: 'rgba(245,146,74,0.14)',
    scrollbar: '#2a3441',
    codeBg: '#0d1117',
    shadow: '0 8px 24px rgba(0,0,0,0.45)',
    shadowSm: '0 2px 8px rgba(0,0,0,0.35)',
  },
  light: {
    name: 'light',
    bg: '#f4f6f9',
    bgSubtle: '#eef1f5',
    sidebarBg: '#ffffff',
    surface: '#ffffff',
    surfaceAlt: '#f7f9fb',
    surfaceHover: '#eef2f6',
    border: '#e2e7ed',
    borderStrong: '#cdd5de',
    textPrimary: '#161b22',
    textSecondary: '#5b6672',
    textTertiary: '#8a94a0',
    accent: '#2f6fe0',
    accentHover: '#255bc2',
    accentSoft: 'rgba(47,111,224,0.09)',
    accentBorder: 'rgba(47,111,224,0.3)',
    green: '#1d9a68', greenSoft: 'rgba(29,154,104,0.1)', greenBorder: 'rgba(29,154,104,0.28)',
    yellow: '#b7791f', yellowSoft: 'rgba(183,121,31,0.1)', yellowBorder: 'rgba(183,121,31,0.28)',
    red: '#d33d38', redSoft: 'rgba(211,61,56,0.1)', redBorder: 'rgba(211,61,56,0.28)',
    gray: '#6b7684', graySoft: 'rgba(107,118,132,0.12)', grayBorder: 'rgba(107,118,132,0.28)',
    orange: '#c05f1f', orangeSoft: 'rgba(192,95,31,0.1)',
    scrollbar: '#d7dde3',
    codeBg: '#0d1117',
    shadow: '0 8px 24px rgba(30,40,60,0.10)',
    shadowSm: '0 2px 8px rgba(30,40,60,0.08)',
  }
};

window.buildInfraData = function buildInfraData() {
  const servers = [
    { id: 'dc01', hostname: 'DC01', os: 'Windows Server 2022', kind: 'windows', role: 'Domain Controller', env: 'production', health: 'healthy', cpu: 22, ram: 41, disk: 38, ip: '10.20.0.11', uptime: '94d 6h' },
    { id: 'dc02', hostname: 'DC02', os: 'Windows Server 2022', kind: 'windows', role: 'Domain Controller (replica)', env: 'production', health: 'healthy', cpu: 15, ram: 33, disk: 29, ip: '10.20.0.12', uptime: '94d 6h' },
    { id: 'web-prod-03', hostname: 'WEB-PROD-03', os: 'Windows Server 2022', kind: 'windows', role: 'IIS Web Server', env: 'production', health: 'warning', cpu: 78, ram: 84, disk: 62, ip: '10.20.1.13', uptime: '41d 2h' },
    { id: 'web-prod-04', hostname: 'WEB-PROD-04', os: 'Windows Server 2022', kind: 'windows', role: 'IIS Web Server', env: 'production', health: 'healthy', cpu: 34, ram: 55, disk: 40, ip: '10.20.1.14', uptime: '41d 2h' },
    { id: 'sql-prod-01', hostname: 'SQL-PROD-01', os: 'Windows Server 2019', kind: 'windows', role: 'SQL Server 2019', env: 'production', health: 'critical', cpu: 96, ram: 91, disk: 88, ip: '10.20.2.10', uptime: '112d 18h' },
    { id: 'app-prod-02', hostname: 'APP-PROD-02', os: 'Ubuntu 22.04 LTS', kind: 'linux', role: 'App Server (Node)', env: 'production', health: 'healthy', cpu: 45, ram: 62, disk: 51, ip: '10.20.3.21', uptime: '30d 4h' },
    { id: 'lb-prod-01', hostname: 'LB-PROD-01', os: 'Ubuntu 22.04 LTS', kind: 'linux', role: 'Load Balancer (nginx)', env: 'production', health: 'healthy', cpu: 18, ram: 30, disk: 22, ip: '10.20.0.5', uptime: '120d 1h' },
    { id: 'file-srv-01', hostname: 'FILE-SRV-01', os: 'Windows Server 2019', kind: 'windows', role: 'File Server', env: 'production', health: 'warning', cpu: 55, ram: 88, disk: 94, ip: '10.20.4.9', uptime: '76d 11h' },
    { id: 'dev-build-01', hostname: 'DEV-BUILD-01', os: 'Ubuntu 20.04 LTS', kind: 'linux', role: 'CI Runner', env: 'development', health: 'healthy', cpu: 12, ram: 28, disk: 35, ip: '10.30.0.4', uptime: '5d 20h' },
    { id: 'cache-prod-01', hostname: 'CACHE-PROD-01', os: 'Ubuntu 22.04 LTS', kind: 'linux', role: 'Redis Cache', env: 'production', health: 'healthy', cpu: 8, ram: 44, disk: 15, ip: '10.20.3.30', uptime: '88d 3h' },
    { id: 'backup-01', hostname: 'BACKUP-01', os: 'Windows Server 2022', kind: 'windows', role: 'Backup Server', env: 'production', health: 'offline', cpu: 0, ram: 0, disk: 0, ip: '10.20.5.2', uptime: '—' },
    { id: 'stage-web-01', hostname: 'STAGE-WEB-01', os: 'Windows Server 2022', kind: 'windows', role: 'IIS Web Server (staging)', env: 'staging', health: 'healthy', cpu: 20, ram: 38, disk: 44, ip: '10.40.1.7', uptime: '12d 9h' },
  ];

  const alerts = [
    { id: 'al-1', severity: 'critical', title: 'Sustained CPU >95% for 12 minutes', server: 'SQL-PROD-01', time: '4 min ago', status: 'open', ai: 'Query plan regression on dbo.Orders — an index rebuild or query hint may resolve this without a restart.' },
    { id: 'al-2', severity: 'critical', title: 'Disk space below 6% free on D:\\', server: 'FILE-SRV-01', time: '22 min ago', status: 'open', ai: 'Shadow copies and stale user profiles are consuming 40GB+. Safe to run automated cleanup script.' },
    { id: 'al-3', severity: 'critical', title: 'Server unreachable — last heartbeat 3h ago', server: 'BACKUP-01', time: '3h ago', status: 'investigating', ai: 'No agent heartbeat and no ping response. Likely power or NIC failure — recommend on-site check.' },
    { id: 'al-4', severity: 'warning', title: 'High memory pressure, GC pauses detected', server: 'WEB-PROD-03', time: '18 min ago', status: 'open', ai: 'App pool memory leak pattern matches last week — recycling the app pool is a safe interim fix.' },
    { id: 'al-5', severity: 'warning', title: 'TLS certificate expires in 9 days', server: 'portal.acmecorp.io', time: '1h ago', status: 'assigned', ai: 'Auto-renewal via ACME is configured but last attempt failed DNS validation.' },
    { id: 'al-6', severity: 'warning', title: '14 failed login attempts for jsmith', server: 'DC01', time: '2h ago', status: 'open', ai: 'All attempts from a single external IP — pattern consistent with password spraying, not user error.' },
    { id: 'al-7', severity: 'warning', title: 'Replication latency above threshold (18 min)', server: 'DC02', time: '35 min ago', status: 'open', ai: 'WAN link saturation between sites during backup window is the likely cause.' },
    { id: 'al-8', severity: 'info', title: 'Windows Updates pending on 4 servers', server: 'Multiple', time: '6h ago', status: 'open', ai: 'KB5034123 cumulative update ready — schedule during next maintenance window.' },
  ];

  const events = [
    { id: 'ev-1', server: 'SQL-PROD-01', time: '10:42:03', level: 'Error', source: 'MSSQLSERVER', eventId: 17053, message: 'A significant part of sql server process memory has been paged out.' },
    { id: 'ev-2', server: 'SQL-PROD-01', time: '10:41:47', level: 'Warning', source: 'MSSQLSERVER', eventId: 701, message: 'There is insufficient system memory in resource pool default to run this query.' },
    { id: 'ev-3', server: 'SQL-PROD-01', time: '10:38:12', level: 'Error', source: 'MSSQLSERVER', eventId: 9002, message: 'The transaction log for database OrdersDB is full.' },
    { id: 'ev-4', server: 'WEB-PROD-03', time: '10:20:55', level: 'Warning', source: 'ASP.NET 4.0.30319.0', eventId: 1310, message: 'Configuration error detected, application restart scheduled.' },
    { id: 'ev-5', server: 'WEB-PROD-03', time: '10:19:02', level: 'Warning', source: 'W3SVC', eventId: 2268, message: 'IIS worker process exceeded memory limit and was recycled.' },
    { id: 'ev-6', server: 'DC01', time: '09:55:31', level: 'Warning', source: 'Microsoft-Windows-Security-Auditing', eventId: 4625, message: 'An account failed to log on. Account Name: jsmith. Source: 203.0.113.44' },
    { id: 'ev-7', server: 'DC01', time: '09:55:12', level: 'Warning', source: 'Microsoft-Windows-Security-Auditing', eventId: 4625, message: 'An account failed to log on. Account Name: jsmith. Source: 203.0.113.44' },
    { id: 'ev-8', server: 'DC02', time: '09:40:00', level: 'Warning', source: 'NTDS Replication', eventId: 2092, message: 'Replication latency with DC01 exceeds configured threshold.' },
    { id: 'ev-9', server: 'FILE-SRV-01', time: '09:12:44', level: 'Error', source: 'Ntfs', eventId: 55, message: 'The file system structure on volume D: is corrupt and unusable.' },
    { id: 'ev-10', server: 'FILE-SRV-01', time: '08:59:20', level: 'Warning', source: 'srv', eventId: 2013, message: 'Disk D: is nearing capacity, 5.4% free space remaining.' },
  ];

  const adOUs = [
    { id: 'corp', name: 'acmecorp.io', type: 'domain', children: [
      { id: 'hq', name: 'HQ', type: 'ou', children: [
        { id: 'sales', name: 'Sales', type: 'ou', children: [] },
        { id: 'eng', name: 'Engineering', type: 'ou', children: [] },
        { id: 'it', name: 'IT', type: 'ou', children: [] },
      ]},
      { id: 'servers-ou', name: 'Servers', type: 'ou', children: [] },
      { id: 'svc', name: 'Service Accounts', type: 'ou', children: [] },
    ]}
  ];

  const adUsers = [
    { id: 'u1', name: 'Jane Smith', sam: 'jsmith', title: 'Sales Director', ou: 'Sales', status: 'locked', lastLogon: '2h ago' },
    { id: 'u2', name: 'Marcus Lee', sam: 'mlee', title: 'Senior Engineer', ou: 'Engineering', status: 'active', lastLogon: '12 min ago' },
    { id: 'u3', name: 'Priya Nair', sam: 'pnair', title: 'DevOps Engineer', ou: 'IT', status: 'active', lastLogon: '3 min ago' },
    { id: 'u4', name: 'Tom Becker', sam: 'tbecker', title: 'Account Executive', ou: 'Sales', status: 'disabled', lastLogon: '44d ago' },
    { id: 'u5', name: 'Ava Chen', sam: 'achen', title: 'IT Administrator', ou: 'IT', status: 'active', lastLogon: '1 min ago' },
    { id: 'u6', name: 'Sam Osei', sam: 'sosei', title: 'Backend Engineer', ou: 'Engineering', status: 'active', lastLogon: '1h ago' },
    { id: 'u7', name: 'Lena Ruiz', sam: 'lruiz', title: 'Sales Rep', ou: 'Sales', status: 'active', lastLogon: '5h ago' },
    { id: 'u8', name: 'svc-backup', sam: 'svc-backup', title: 'Service Account', ou: 'Service Accounts', status: 'active', lastLogon: '9h ago' },
  ];

  const adGroups = [
    { id: 'g1', name: 'Domain Admins', members: 4, scope: 'Global / Security' },
    { id: 'g2', name: 'IT-Support', members: 6, scope: 'Global / Security' },
    { id: 'g3', name: 'Sales-Team', members: 18, scope: 'Global / Distribution' },
    { id: 'g4', name: 'VPN-Users', members: 42, scope: 'Global / Security' },
  ];

  const scripts = [
    { id: 's1', name: 'CreateLocalUserAccount', risk: 'low', code: "New-LocalUser -Name 'ServiceAccount' -Description 'Service account for web production' -AccountNeverExpires -WhatIf" },
    { id: 's2', name: 'Restart-Server', risk: 'high', code: 'Restart-Computer -Force -WhatIf' },
    { id: 's3', name: 'Restart-W3SVC', risk: 'medium', code: "Restart-Service -Name 'W3SVC' -Force -WhatIf" },
    { id: 's4', name: 'Disable-USBStorage', risk: 'medium', code: "Set-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\USBSTOR' -Name 'Start' -Value 4 -WhatIf" },
    { id: 's5', name: 'Get-FailedLogins', risk: 'low', code: "Get-WinEvent -FilterHashtable @{LogName='Security';Id=4625} -MaxEvents 50" },
    { id: 's6', name: 'Unlock-ADUser', risk: 'low', code: "Unlock-ADAccount -Identity 'jsmith' -WhatIf" },
  ];

  const automations = [
    { id: 'wf1', name: 'Nightly backup verification', trigger: 'Schedule — 02:00 daily', condition: 'Backup job status = Failed', action: 'Notify Slack #ops + retry job', status: 'active', lastRun: '6h ago', result: 'success' },
    { id: 'wf2', name: 'Auto-remediate low disk space', trigger: 'Metric — Disk free < 10%', condition: 'Server role = File/Web server', action: 'Run Clear-DiskSpace.ps1, notify on completion', status: 'active', lastRun: '2h ago', result: 'success' },
    { id: 'wf3', name: 'Certificate expiry notifier', trigger: 'Schedule — daily 09:00', condition: 'Cert expiry < 14 days', action: 'Create alert + email security team', status: 'active', lastRun: '5h ago', result: 'success' },
    { id: 'wf4', name: 'Failed login lockout responder', trigger: 'Event 4625 x10 in 5 min', condition: 'Source IP is external', action: 'Lock account, notify SOC, open alert', status: 'paused', lastRun: '2d ago', result: 'success' },
  ];

  const dns = { zones: [
      { name: 'acmecorp.io', type: 'Primary', records: 48, health: 'healthy' },
      { name: 'corp.acmecorp.io', type: 'Primary', records: 22, health: 'warning' },
      { name: '20.20.10.in-addr.arpa', type: 'Reverse', records: 12, health: 'healthy' },
    ], issues: [
      { type: 'Missing record', detail: 'No PTR record for WEB-PROD-04 (10.20.1.14)' },
      { type: 'Duplicate record', detail: 'Two A records for portal.acmecorp.io point to different IPs' },
    ]};

  const dhcp = { scopes: [
      { name: 'HQ-LAN', range: '10.20.1.0/24', leased: 184, total: 254, util: 72 },
      { name: 'HQ-VPN', range: '10.20.9.0/24', leased: 41, total: 254, util: 16 },
      { name: 'Guest-WiFi', range: '10.60.0.0/22', leased: 210, total: 1022, util: 21 },
    ], conflicts: 1 };

  const chatSeed = [
    { role: 'user', content: 'Why is SQL-PROD-01 slow?' },
    { role: 'assistant', thinking: true,
      tools: [
        { name: 'Query performance metrics', target: 'SQL-PROD-01', status: 'done' },
        { name: 'Analyze recent event logs', target: 'SQL-PROD-01', status: 'done' },
      ],
      content: "SQL-PROD-01 has been running at 96% CPU for the last 12 minutes, with paired memory-pressure events in the log (17053, 701) and a full transaction log warning (9002).\n\nThis pattern matches a **query plan regression** on `dbo.Orders` after last night's statistics update — not a resource shortage. Rebuilding the affected index should bring it back to baseline without a restart.",
      script: { name: 'Rebuild-OrdersIndex', risk: 'medium', code: "Invoke-Sqlcmd -ServerInstance 'SQL-PROD-01' -Query \"ALTER INDEX ALL ON dbo.Orders REBUILD WITH (ONLINE = ON)\"" }
    }
  ];

  const examplePrompts = [
    'Why is Server01 slow?',
    'Restart IIS on WEB-PROD-03',
    'Generate PowerShell to disable USB storage',
    'Show failed login attempts today',
    'Unlock AD user jsmith',
    'Analyze event logs on SQL-PROD-01',
  ];

  const recentConversations = [
    { id: 'c1', title: 'Why is SQL-PROD-01 slow?', time: '4 min ago', active: true },
    { id: 'c2', title: 'Disable USB storage fleet-wide', time: '1h ago' },
    { id: 'c3', title: 'Unlock jsmith account', time: '2h ago' },
    { id: 'c4', title: 'Certificate renewal for portal.acmecorp.io', time: 'Yesterday' },
    { id: 'c5', title: 'Weekly patch compliance summary', time: '2 days ago' },
  ];

  return { servers, alerts, events, adOUs, adUsers, adGroups, scripts, automations, dns, dhcp, chatSeed, examplePrompts, recentConversations };
};
