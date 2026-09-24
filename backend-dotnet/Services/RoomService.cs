using backend_dotnet.Common;
using backend_dotnet.DTOs;
using backend_dotnet.Repositories;

namespace backend_dotnet.Services;

public interface IRoomService
{
    Task<Result<List<RoomDto>>> GetAvailableRoomsAsync(DateTime? checkIn, DateTime? checkOut, string? roomType, CancellationToken ct = default);
    Task<Result<RoomDto>> GetByIdAsync(int id, CancellationToken ct = default);
}

public class RoomService(IRoomRepository roomRepository, ILogger<RoomService> logger) : IRoomService
{
    public async Task<Result<List<RoomDto>>> GetAvailableRoomsAsync(DateTime? checkIn, DateTime? checkOut, string? roomType, CancellationToken ct = default)
    {
        if (checkIn.HasValue && checkOut.HasValue)
        {
            if (checkIn.Value.Date < DateTime.UtcNow.Date)
            {
                return Result<List<RoomDto>>.Failure("Check-in date cannot be in the past.", 400);
            }

            if (checkOut.Value.Date <= checkIn.Value.Date)
            {
                return Result<List<RoomDto>>.Failure("Check-out date must be after check-in date.", 400);
            }
        }

        try
        {
            var rooms = await roomRepository.GetAvailableRoomsAsync(checkIn, checkOut, roomType, ct);
            var dtos = rooms.Select(r => new RoomDto(
                r.Id,
                r.Name,
                r.Type,
                r.PricePerNight,
                r.Capacity,
                r.Description,
                r.Amenities,
                true
            )).ToList();

            return Result<List<RoomDto>>.Success(dtos);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Error querying available rooms for checkIn={CheckIn}, checkOut={CheckOut}, type={Type}", checkIn, checkOut, roomType);
            return Result<List<RoomDto>>.Failure("Unable to retrieve room availability due to internal server error.", 500);
        }
    }

    public async Task<Result<RoomDto>> GetByIdAsync(int id, CancellationToken ct = default)
    {
        var room = await roomRepository.GetByIdAsync(id, ct);
        if (room is null)
        {
            return Result<RoomDto>.NotFound($"Room with ID {id} was not found.");
        }

        return Result<RoomDto>.Success(new RoomDto(
            room.Id,
            room.Name,
            room.Type,
            room.PricePerNight,
            room.Capacity,
            room.Description,
            room.Amenities,
            room.IsActive
        ));
    }
}
