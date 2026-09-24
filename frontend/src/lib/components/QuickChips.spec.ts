import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import QuickChips from './QuickChips.svelte';

describe('QuickChips Component', () => {
	it('should render all quick query chips', () => {
		const handleSelect = vi.fn();
		const { getByText } = render(QuickChips, { onSelect: handleSelect });

		expect(getByText(/เวลาเช็คอิน & เช็คเอาต์/)).toBeDefined();
		expect(getByText(/ตรวจสอบห้องว่างสัปดาห์นี้/)).toBeDefined();
		expect(getByText(/อาหารเช้า & บุฟเฟต์/)).toBeDefined();
	});

	it('should invoke onSelect callback with query text when a chip is clicked', async () => {
		const handleSelect = vi.fn();
		const { getByText } = render(QuickChips, { onSelect: handleSelect });

		const chip = getByText(/เวลาเช็คอิน & เช็คเอาต์/);
		await fireEvent.click(chip);

		expect(handleSelect).toHaveBeenCalledTimes(1);
		expect(handleSelect).toHaveBeenCalledWith(
			expect.stringContaining('เวลาเช็คอินและเช็คเอาต์ของโรงแรมกี่โมง')
		);
	});
});
