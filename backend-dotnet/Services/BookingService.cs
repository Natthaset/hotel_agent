using backend_dotnet.Common;
using backend_dotnet.DTOs;
using backend_dotnet.Models;
using backend_dotnet.Repositories;

namespace backend_dotnet.Services;

public interface IBookingService
{
    Task<Result<BookingResponseDto>> CreateBookingAsync(BookingRequestDto request, CancellationToken ct = default);
    Task<Result<BookingResponseDto>> GetByIdAsync(int id, CancellationToken ct = default);
}

public class BookingService(
    IBookingRepository bookingRepository,
    IRoomRepository roomRepository,
    ILogger<BookingService> logger) : IBookingService
{
    public async Task<Result<BookingResponseDto>> CreateBookingAsync(BookingRequestDto request, CancellationToken ct = default)
    {
        // 1. Validate dates
        var checkIn = request.CheckInDate.Date;
        var checkOut = request.CheckOutDate.Date;
        var today = DateTime.UtcNow.Date;

        if (checkIn < today)
        {
            return Result<BookingResponseDto>.Failure("Check-in date cannot be in the past.", 400);
        }

        if (checkOut <= checkIn)
        {
            return Result<BookingResponseDto>.Failure("Check-out date must be at least one day after check-in date.", 400);
        }

        var nights = (int)(checkOut - checkIn).TotalDays;
        if (nights > 30)
        {
            return Result<BookingResponseDto>.Failure("Bookings longer than 30 consecutive nights require special executive concierge handling.", 400);
        }

        // 2. Validate Room existence
        var room = await roomRepository.GetByIdAsync(request.RoomId, ct);
        if (room is null || !room.IsActive)
        {
            return Result<BookingResponseDto>.Failure($"Room ID {request.RoomId} does not exist or is currently inactive.", 400);
        }

        // 3. Validate Capacity
        if (request.Pax > room.Capacity)
        {
            return Result<BookingResponseDto>.Failure(
                $"Requested party size ({request.Pax} guests) exceeds maximum capacity ({room.Capacity} guests) for {room.Name}.", 400);
        }

        // 4. Check Room Availability for the selected dates
        var isAvailable = await roomRepository.IsRoomAvailableAsync(room.Id, checkIn, checkOut, ct);
        if (!isAvailable)
        {
            return Result<BookingResponseDto>.Failure(
                $"Apologies, {room.Name} is already reserved for the selected dates ({checkIn:yyyy-MM-dd} to {checkOut:yyyy-MM-dd}). Please select another date or room category.", 400);
        }

        // 5. Calculate Price & Create Entity
        var totalPrice = room.PricePerNight * nights;
        var booking = new Booking
        {
            CustomerName = request.CustomerName.Trim(),
            CheckInDate = checkIn,
            CheckOutDate = checkOut,
            RoomId = room.Id,
            Pax = request.Pax,
            TotalPrice = totalPrice,
            Status = "Confirmed",
            CreatedAt = DateTime.UtcNow
        };

        try
        {
            var savedBooking = await bookingRepository.CreateAsync(booking, ct);
            logger.LogInformation("Successfully created booking {BookingId} for {Customer} in Room {RoomId} ({Nights} nights, Total: {Total})",
                savedBooking.Id, savedBooking.CustomerName, savedBooking.RoomId, nights, totalPrice);

            var responseDto = new BookingResponseDto(
                savedBooking.Id,
                savedBooking.CustomerName,
                savedBooking.CheckInDate,
                savedBooking.CheckOutDate,
                room.Id,
                room.Name,
                room.Type,
                savedBooking.Pax,
                savedBooking.TotalPrice,
                nights,
                savedBooking.Status,
                savedBooking.CreatedAt
            );

            return Result<BookingResponseDto>.Success(responseDto, 201);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to persist booking for customer {CustomerName}", request.CustomerName);
            return Result<BookingResponseDto>.Failure("Failed to complete reservation due to unexpected server error.", 500);
        }
    }

    public async Task<Result<BookingResponseDto>> GetByIdAsync(int id, CancellationToken ct = default)
    {
        var booking = await bookingRepository.GetByIdAsync(id, ct);
        if (booking is null)
        {
            return Result<BookingResponseDto>.NotFound($"Booking with ID {id} was not found.");
        }

        var nights = (int)(booking.CheckOutDate.Date - booking.CheckInDate.Date).TotalDays;
        var roomName = booking.Room?.Name ?? "Standard Room";
        var roomType = booking.Room?.Type ?? "Standard";

        var responseDto = new BookingResponseDto(
            booking.Id,
            booking.CustomerName,
            booking.CheckInDate,
            booking.CheckOutDate,
            booking.RoomId,
            roomName,
            roomType,
            booking.Pax,
            booking.TotalPrice,
            nights,
            booking.Status,
            booking.CreatedAt
        );

        return Result<BookingResponseDto>.Success(responseDto);
    }
}
