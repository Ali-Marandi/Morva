import React, { useEffect, useRef, useState } from 'react';
import { ArrowLeft, Menu, ShieldCheck, User, X } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ModuleItem, moduleMenus } from '../../config/moduleNavigation';

function containsModule(item: ModuleItem, targetId: string): boolean {
  return item.id === targetId || Boolean(item.children?.some((child) => containsModule(child, targetId)));
}

function Topbar() {
  const [activeMenu, setActiveMenu] = useState<string | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const mobileMenuButtonRef = useRef<HTMLButtonElement>(null);
  const current = moduleMenus.find((menu) => menu.id === activeMenu);
  const currentModuleId = location.pathname.startsWith('/modules/')
    ? location.pathname.split('/').filter(Boolean).pop() || null
    : null;

  useEffect(() => {
    setActiveMenu(null);
    setMobileOpen(false);
  }, [location.pathname]);

  const openPage = (item: ModuleItem) => {
    navigate('/modules/' + item.id);
    setActiveMenu(null);
    setMobileOpen(false);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLElement>) => {
    if (event.key !== 'Escape' || (!activeMenu && !mobileOpen)) return;
    event.preventDefault();
    const focusTarget = activeMenu
      ? document.getElementById('morva-module-trigger-' + activeMenu)
      : mobileMenuButtonRef.current;
    setActiveMenu(null);
    setMobileOpen(false);
    focusTarget?.focus();
  };

  const handleBlur = (event: React.FocusEvent<HTMLElement>) => {
    if (event.currentTarget.contains(event.relatedTarget as Node | null)) return;
    setActiveMenu(null);
    setMobileOpen(false);
  };

  return (
    <header
      className="relative z-50 bg-[#244da8] text-white shadow-md"
      dir="rtl"
      onMouseLeave={() => setActiveMenu(null)}
      onKeyDown={handleKeyDown}
      onBlur={handleBlur}
    >
      <div className="flex min-h-14 items-center px-3 lg:px-5">
        <div className="ml-4 hidden items-center gap-2 whitespace-nowrap xl:flex">
          <div className="flex h-8 w-8 items-center justify-center rounded-full border border-white/50" aria-hidden="true">
            <ShieldCheck size={18} />
          </div>
          <span className="text-sm font-bold">سیستم حقوق و دستمزد</span>
        </div>

        <nav className="hidden flex-1 items-center overflow-x-auto md:flex" aria-label="ماژول‌های سامانه">
          {moduleMenus.map((menu) => {
            const Icon = menu.icon;
            const isOpen = activeMenu === menu.id;
            const isCurrent = Boolean(currentModuleId && containsModule(menu, currentModuleId));
            const triggerId = 'morva-module-trigger-' + menu.id;
            const panelId = 'morva-module-panel-' + menu.id;

            return (
              <button
                key={menu.id}
                id={triggerId}
                type="button"
                aria-expanded={isOpen}
                aria-controls={panelId}
                aria-current={isCurrent ? 'page' : undefined}
                onMouseEnter={() => setActiveMenu(menu.id)}
                onClick={() => setActiveMenu(isOpen ? null : menu.id)}
                className={'flex shrink-0 items-center gap-2 rounded-t-xl px-3 py-3.5 text-sm font-semibold transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-amber-300 ' + (isOpen ? 'bg-white text-[#244da8]' : isCurrent ? 'bg-white/15 text-white' : 'hover:bg-white/15')}
              >
                <Icon size={17} aria-hidden="true" />
                {menu.label}
              </button>
            );
          })}
        </nav>

        <div className="mr-auto hidden items-center gap-2 border-r border-white/30 pr-3 sm:flex md:mr-2">
          <div className="text-left leading-tight">
            <p className="text-xs font-medium">مدیر سامانه</p>
            <p className="text-[10px] text-white/70">حساب محلی</p>
          </div>
          <User size={20} aria-hidden="true" />
        </div>

        <button
          ref={mobileMenuButtonRef}
          type="button"
          className="mr-auto inline-flex items-center justify-center rounded-lg p-2 transition-colors hover:bg-white/15 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-300 md:hidden"
          onClick={() => setMobileOpen((open) => !open)}
          aria-label={mobileOpen ? 'بستن منوی ماژول‌ها' : 'باز کردن منوی ماژول‌ها'}
          aria-expanded={mobileOpen}
          aria-controls="morva-mobile-module-navigation"
        >
          {mobileOpen ? <X size={21} aria-hidden="true" /> : <Menu size={21} aria-hidden="true" />}
        </button>
      </div>

      <nav
        id="morva-mobile-module-navigation"
        aria-label="منوی ماژول‌ها در موبایل"
        aria-hidden={!mobileOpen}
        hidden={!mobileOpen}
        className={'absolute right-0 left-0 top-full border-t border-white/15 bg-white p-3 text-slate-800 shadow-xl md:hidden ' + (mobileOpen ? 'block' : 'hidden')}
      >
        <p className="px-2 pb-2 pt-1 text-xs font-semibold text-slate-500">انتخاب بخش سامانه</p>
        <div className="grid gap-2 sm:grid-cols-2">
          {moduleMenus.map((menu) => {
            const Icon = menu.icon;
            const isCurrent = location.pathname === '/modules/' + menu.id;
            return (
              <Link
                key={menu.id}
                to={'/modules/' + menu.id}
                onClick={() => setMobileOpen(false)}
                aria-current={isCurrent ? 'page' : undefined}
                tabIndex={mobileOpen ? 0 : -1}
                className={'flex min-h-14 items-center gap-3 rounded-xl border px-3 py-3 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 ' + (isCurrent ? 'border-blue-300 bg-blue-50 text-blue-900' : 'border-slate-200 bg-white text-slate-800 hover:border-blue-200 hover:bg-blue-50/60')}
              >
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-[#244da8]">
                  <Icon size={18} aria-hidden="true" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-bold">{menu.label}</span>
                  <span className="mt-0.5 block text-xs text-slate-500">{menu.children?.length || 0} بخش مرتبط</span>
                </span>
                <ArrowLeft size={16} className="shrink-0 text-slate-400" aria-hidden="true" />
              </Link>
            );
          })}
        </div>
      </nav>

      {current && (
        <MegaMenu
          menu={current}
          panelId={'morva-module-panel-' + current.id}
          triggerId={'morva-module-trigger-' + current.id}
          onSelect={openPage}
        />
      )}
    </header>
  );
}

function MegaMenu({
  menu,
  panelId,
  triggerId,
  onSelect,
}: {
  menu: (typeof moduleMenus)[number];
  panelId: string;
  triggerId: string;
  onSelect: (item: ModuleItem) => void;
}) {
  return (
    <div
      id={panelId}
      role="region"
      aria-labelledby={triggerId}
      className="absolute right-3 left-3 top-full rounded-b-2xl bg-white p-5 text-slate-800 shadow-2xl ring-1 ring-black/10 md:left-auto md:w-[min(920px,calc(100vw-24px))]"
    >
      <div className="mb-4 flex items-center justify-between gap-3 border-b border-slate-100 pb-3">
        <div>
          <p className="text-base font-bold text-slate-900">{menu.label}</p>
          <p className="mt-0.5 text-xs text-slate-500">دسترسی سریع به بخش‌های مرتبط</p>
        </div>
        <button
          type="button"
          onClick={() => onSelect(menu)}
          className="inline-flex shrink-0 items-center gap-1 rounded-md text-sm font-medium text-[#2855b5] hover:text-[#173979] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
        >
          نمای کلی <ArrowLeft size={16} aria-hidden="true" />
        </button>
      </div>
      <div className="grid gap-x-6 gap-y-2 md:grid-cols-2 lg:grid-cols-3">
        {menu.children?.map((item) => (
          <section key={item.id} className="rounded-xl border border-slate-100 bg-slate-50/70 p-3 transition-colors hover:border-blue-100 hover:bg-blue-50/60">
            <button
              type="button"
              onClick={() => onSelect(item)}
              className="flex w-full items-center justify-between rounded-md text-right text-sm font-bold text-slate-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
            >
              <span>{item.label}</span>
              <ArrowLeft size={16} className="text-[#4d7ee8]" aria-hidden="true" />
            </button>
            {item.children && (
              <div className="mt-2 space-y-1 border-r border-blue-100 pr-3">
                {item.children.map((child) => (
                  <button
                    key={child.id}
                    type="button"
                    onClick={() => onSelect(child)}
                    className="block w-full rounded-md px-1 py-1.5 text-right text-xs text-slate-600 hover:bg-white hover:text-[#1d4ba9] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-blue-600"
                  >
                    {child.label}
                  </button>
                ))}
              </div>
            )}
          </section>
        ))}
      </div>
    </div>
  );
}

export default Topbar;
