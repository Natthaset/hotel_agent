import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import BookingConfirmationCard from './BookingConfirmationCard.svelte';
import type { BookingData } from '$lib/types/chat';

describe('BookingConfirmationCard Component', () => {
	const mockBooking: BookingData = {
		id: 101,
		customerName: 'Khun Somchai Jaidee',
		checkInDate: '2026-10-01T00:00:00Z',
		checkOutDate: '2026-10-04T00:00:00Z',
		roomId: 1,
		roomName: 'Deluxe Ocean King',
		roomType: 'Deluxe King',
		pax: 2,
		totalPrice: 19500,
		totalNights: 3,
		status: 'Confirmed',
		createdAt: '2026-09-24T12:00:00Z'
	};

	it('should render booking reference code and confirmed header', () => {
		const { getByText } = render(BookingConfirmationCard, { booking: mockBooking });

		expect(getByText(/RESERVATION CONFIRMED/)).toBeDefined();
		expect(getByText('GA-00101')).toBeDefined();
	});

	it('should render customer details and room information correctly', () => {
		const { getByText } = render(BookingConfirmationCard, { booking: mockBooking });

		expect(getByText('Khun Somchai Jaidee')).toBeDefined();
		expect(getByText(/Deluxe Ocean King/)).toBeDefined();
		expect(getByText(/3 คืน/)).toBeDefined();
		expect(getByText(/2 ท่าน/)).toBeDefined();
	});

	it('should format total price in THB currency', () => {
		const { getByText } = render(BookingConfirmationCard, { booking: mockBooking });

		// Thai currency formatter: ฿19,500 or THB 19,500
		expect(getByText(/19,500/)).toBeDefined();
	});
});
