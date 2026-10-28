import { Folder, Search, FileText, ShieldAlert, History, LogOut } from "lucide-react";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-slate-50">
      {/* Sidebar */}
      <div className="w-64 bg-slate-900 text-white flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-slate-800">
          <ShieldAlert className="h-6 w-6 text-blue-500 mr-2" />
          <span className="font-bold text-lg tracking-tight">MHA-DMS</span>
        </div>
        <div className="flex-1 py-6 px-4 space-y-2">
          <a href="/dashboard" className="flex items-center px-4 py-2 bg-blue-600/20 text-blue-400 rounded-md font-medium">
            <Folder className="h-5 w-5 mr-3" /> My Cases
          </a>
          <a href="#" className="flex items-center px-4 py-2 text-slate-400 hover:bg-slate-800 hover:text-slate-200 rounded-md font-medium transition-colors">
            <Search className="h-5 w-5 mr-3" /> Advanced Search
          </a>
          <a href="#" className="flex items-center px-4 py-2 text-slate-400 hover:bg-slate-800 hover:text-slate-200 rounded-md font-medium transition-colors">
            <History className="h-5 w-5 mr-3" /> Audit Logs
          </a>
          <a href="#" className="flex items-center px-4 py-2 text-slate-400 hover:bg-slate-800 hover:text-slate-200 rounded-md font-medium transition-colors">
            <FileText className="h-5 w-5 mr-3" /> Approvals
          </a>
        </div>
        <div className="p-4 border-t border-slate-800">
          <div className="flex items-center">
            <div className="h-8 w-8 rounded-full bg-slate-700 flex items-center justify-center text-sm font-bold">IO</div>
            <div className="ml-3">
              <p className="text-sm font-medium">Insp. R. Kumar</p>
              <p className="text-xs text-slate-400">LEAD_IO | CBI</p>
            </div>
          </div>
          <a href="/login" className="mt-4 flex items-center text-sm text-slate-400 hover:text-white transition-colors">
            <LogOut className="h-4 w-4 mr-2" /> Secure Logout
          </a>
        </div>
      </div>
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6 shadow-sm z-10">
          <h1 className="text-xl font-semibold text-slate-800">Case Dashboard</h1>
          <div className="flex items-center space-x-4">
            <span className="px-3 py-1 bg-green-100 text-green-800 text-xs font-bold rounded-full border border-green-200 flex items-center">
              <span className="w-2 h-2 rounded-full bg-green-500 mr-2 animate-pulse"></span>
              Vault Connected
            </span>
          </div>
        </header>
        <main className="flex-1 overflow-auto bg-slate-50 p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
