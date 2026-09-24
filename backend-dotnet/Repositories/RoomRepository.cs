using backend_dotnet.Data;
using backend_dotnet.Models;
using Microsoft.EntityFrameworkCore;

namespace backend_dotnet.Repositories;

public interface IRoomRepository
{
    Task<List<Room>> GetAvailableRoomsAsync(DateTime? checkIn, DateTime? checkOut, string? roomType, CancellationToken ct = default);
    Task<Room?> GetByIdAsync(int id, CancellationToken ct = default);
    Task<bool> IsRoomAvailableAsync(int roomId, DateTime checkIn, DateTime checkOut, CancellationToken ct = default);
}

public class RoomRepository(HotelDbContext db) : IRoomRepository
{
    public async Task<List<Room>> GetAvailableRoomsAsync(DateTime? checkIn, DateTime? checkOut, string? roomType, CancellationToken ct = default)
    {
        var query = db.Rooms.AsNoTracking().Where(r => r.IsActive);

        if (!string.IsNullOrWhiteSpace(roomType))
        {
            var cleanType = roomType.Trim().ToLower();
            var genericTerms = new[] { "room", "rental", "rental room", "hotel", "rooms", "ห้อง", "ห้องพัก", "ห้องเช่า" };
            if (!genericTerms.Contains(cleanType))
            {
                query = query.Where(r => r.Type.ToLower().Contains(cleanType) || r.Name.ToLower().Contains(cleanType));
            }
        }

        if (checkIn.HasValue && checkOut.HasValue)
        {
            var start = checkIn.Value.Date;
            var end = checkOut.Value.Date;

            // Find rooms that have conflicting bookings
            var bookedRoomIds = await db.Bookings
                .AsNoTracking()
                .Where(b => b.Status != "Cancelled" &&
                            b.CheckInDate < end &&
                            b.CheckOutDate > start)
                .Select(b => b.RoomId)
                .Distinct()
                .ToListAsync(ct);

            query = query.Where(r => !bookedRoomIds.Contains(r.Id));
        }

        return await query.ToListAsync(ct);
    }

    public async Task<Room?> GetByIdAsync(int id, CancellationToken ct = default)
    {
        return await db.Rooms.AsNoTracking().FirstOrDefaultAsync(r => r.Id == id, ct);
    }

    public async Task<bool> IsRoomAvailableAsync(int roomId, DateTime checkIn, DateTime checkOut, CancellationToken ct = default)
    {
        var start = checkIn.Date;
        var end = checkOut.Date;

        var hasOverlap = await db.Bookings
            .AsNoTracking()
            .AnyAsync(b => b.RoomId == roomId &&
                           b.Status != "Cancelled" &&
                           b.CheckInDate < end &&
                           b.CheckOutDate > start, ct);

        return !hasOverlap;
    }
}
