import '@testing-library/jest-dom/vitest';
import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import Topbar from '../components/layout/Topbar';

describe('Topbar navigation', () => {
  it('announces the open module panel and closes it with Escape, returning focus to its toggle', () => {
    render(
      <MemoryRouter>
        <Topbar />
      </MemoryRouter>,
    );

    const toggle = screen.getByRole('button', { name: 'اطلاعات پایه' });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');

    fireEvent.click(toggle);

    const panel = screen.getByRole('region', { name: 'اطلاعات پایه' });
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(toggle).toHaveAttribute('aria-controls', panel.id);

    fireEvent.keyDown(window, { key: 'Escape' });

    expect(screen.queryByRole('region', { name: 'اطلاعات پایه' })).not.toBeInTheDocument();
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(toggle).toHaveFocus();
  });
});
