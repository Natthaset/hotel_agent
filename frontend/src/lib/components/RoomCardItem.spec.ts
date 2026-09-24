import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import RoomCardItem from './RoomCardItem.svelte';
import type { RoomCard } from '$lib/types/chat';

describe('RoomCardItem Component', () => {
	const mockRoom: RoomCard = {
		id: 5,
		name: 'Royal Beachfront Penthouse',
		type: 'Penthouse',
		pricePerNight: 28000,
		capacity: 6,
		description: 'Top-floor ultra-luxury presidential penthouse with private rooftop pool.',
		amenities: 'Private Infinity Pool, 24/7 Butler, Wine Cellar',
		isAvailable: true
	};

	it('should render room name, description, capacity, and price', () => {
		const handleSelect = vi.fn();
		const { getByText } = render(RoomCardItem, { room: mockRoom, onSelect: handleSelect });

		expect(getByText('Royal Beachfront Penthouse')).toBeDefined();
		expect(getByText(/Top-floor ultra-luxury/)).toBeDefined();
		expect(getByText(/สำหรับ 6 ท่าน/)).toBeDefined();
		expect(getByText(/28,000/)).toBeDefined();
	});

	it('should render top amenities pills', () => {
		const handleSelect = vi.fn();
		const { getByText } = render(RoomCardItem, { room: mockRoom, onSelect: handleSelect });

		expect(getByText(/Private Infinity Pool/)).toBeDefined();
		expect(getByText(/24\/7 Butler/)).toBeDefined();
		expect(getByText(/Wine Cellar/)).toBeDefined();
	});

	it('should trigger onSelect when "จองห้องนี้ทันที" button is clicked', async () => {
		const handleSelect = vi.fn();
		const { getByText } = render(RoomCardItem, { room: mockRoom, onSelect: handleSelect });

		const bookButton = getByText('จองห้องนี้ทันที');
		await fireEvent.click(bookButton);

		expect(handleSelect).toHaveBeenCalledTimes(1);
		expect(handleSelect).toHaveBeenCalledWith(mockRoom);
	});
});
