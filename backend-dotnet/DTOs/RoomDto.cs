namespace backend_dotnet.DTOs;

public record RoomDto(
    int Id,
    string Name,
    string Type,
    decimal PricePerNight,
    int Capacity,
    string Description,
    string Amenities,
    bool IsAvailable
);
