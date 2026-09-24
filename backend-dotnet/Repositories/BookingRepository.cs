using backend_dotnet.Data;
using backend_dotnet.Models;
using Microsoft.EntityFrameworkCore;

namespace backend_dotnet.Repositories;

public interface IBookingRepository
{
    Task<Booking> CreateAsync(Booking booking, CancellationToken ct = default);
    Task<Booking?> GetByIdAsync(int id, CancellationToken ct = default);
    Task<List<Booking>> GetByRoomAndDatesAsync(int roomId, DateTime checkIn, DateTime checkOut, CancellationToken ct = default);
}

public class BookingRepository(HotelDbContext db) : IBookingRepository
{
    public async Task<Booking> CreateAsync(Booking booking, CancellationToken ct = default)
    {
        db.Bookings.Add(booking);
        await db.SaveChangesAsync(ct);
        return booking;
    }

    public async Task<Booking?> GetByIdAsync(int id, CancellationToken ct = default)
    {
        return await db.Bookings
            .Include(b => b.Room)
            .AsNoTracking()
            .FirstOrDefaultAsync(b => b.Id == id, ct);
    }

    public async Task<List<Booking>> GetByRoomAndDatesAsync(int roomId, DateTime checkIn, DateTime checkOut, CancellationToken ct = default)
    {
        var start = checkIn.Date;
        var end = checkOut.Date;

        return await db.Bookings
            .AsNoTracking()
            .Where(b => b.RoomId == roomId &&
                        b.Status != "Cancelled" &&
                        b.CheckInDate < end &&
                        b.CheckOutDate > start)
            .ToListAsync(ct);
    }
}
