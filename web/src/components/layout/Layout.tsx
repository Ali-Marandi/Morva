import React from "react";
import { Outlet, useLocation } from "react-router-dom";
import Topbar from "./Topbar";
import Sidebar from "./Sidebar";

function SkipLink() {
  return <a className="skip-link" href="#main-content">رفتن به محتوای اصلی</a>;
}

function Layout() {
  const location = useLocation();
  const isModulePage = location.pathname.startsWith('/modules/');

  if (isModulePage) {
    return (
      <div className="h-screen overflow-hidden bg-slate-100" dir="rtl">
        <SkipLink />
        <Topbar />
        <main id="main-content" tabIndex={-1} className="h-[calc(100vh-48px)] overflow-auto">
          <Outlet />
        </main>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col-reverse bg-morva-50 md:flex-row" dir="rtl">
      <SkipLink />
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar />
        <main id="main-content" tabIndex={-1} className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default Layout;
