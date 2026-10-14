import '@testing-library/jest-dom/vitest';
import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import Sidebar from '../components/layout/Sidebar';

function renderSidebar(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Sidebar />
    </MemoryRouter>,
  );
}

describe('Sidebar navigation', () => {
  it('marks only the current service link active and provides a direct payslip link', () => {
    renderSidebar('/self-service');

    const activeLinks = screen.getAllByRole('link').filter(
      (link) => link.getAttribute('aria-current') === 'page',
    );

    expect(activeLinks).toHaveLength(1);
    expect(activeLinks[0]).toHaveTextContent('خدمات کارکنان');
    expect(screen.getByRole('link', { name: 'فیش‌های حقوقی' })).toHaveAttribute(
      'href',
      '/self-service#payslips',
    );
  });

  it('marks the payslip section as active when its deep link is selected', () => {
    renderSidebar('/self-service#payslips');

    const activeLinks = screen.getAllByRole('link').filter(
      (link) => link.getAttribute('aria-current') === 'page',
    );

    expect(activeLinks).toHaveLength(1);
    expect(activeLinks[0]).toHaveTextContent('فیش‌های حقوقی');
  });

  it('exposes the mobile menu state to assistive technology', () => {
    renderSidebar('/');

    const menuButton = screen.getByRole('button', { name: 'بازکردن منو' });
    expect(menuButton).toHaveAttribute('aria-expanded', 'false');

    fireEvent.click(menuButton);

    expect(screen.getByRole('button', { name: 'بستن منو' })).toHaveAttribute(
      'aria-expanded',
      'true',
    );
  });
});
