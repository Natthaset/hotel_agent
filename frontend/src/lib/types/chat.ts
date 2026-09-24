export interface RoomCard {
  id: number;
  name: string;
  type: string;
  pricePerNight: number;
  capacity: number;
  description: string;
  amenities: string;
  isAvailable?: boolean;
}

export interface BookingData {
  id: number;
  customerName: string;
  checkInDate: string;
  checkOutDate: string;
  roomId: number;
  roomName: string;
  roomType: string;
  pax: number;
  totalPrice: number;
  totalNights: number;
  status: string;
  createdAt: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  roomCards?: RoomCard[];
  bookingData?: BookingData;
  isStreaming?: boolean;
  timestamp: string;
}
