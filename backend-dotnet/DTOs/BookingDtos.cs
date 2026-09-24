using System.ComponentModel.DataAnnotations;

namespace backend_dotnet.DTOs;

public record BookingRequestDto(
    [Required(ErrorMessage = "Customer name is required.")]
    [StringLength(150, MinimumLength = 2, ErrorMessage = "Customer name must be between 2 and 150 characters.")]
    string CustomerName,

    [Required(ErrorMessage = "Check-in date is required.")]
    DateTime CheckInDate,

    [Required(ErrorMessage = "Check-out date is required.")]
    DateTime CheckOutDate,

    [Range(1, int.MaxValue, ErrorMessage = "Valid RoomId is required.")]
    int RoomId,

    [Range(1, 10, ErrorMessage = "Pax must be between 1 and 10 guests.")]
    int Pax
);

public record BookingResponseDto(
    int Id,
    string CustomerName,
    DateTime CheckInDate,
    DateTime CheckOutDate,
    int RoomId,
    string RoomName,
    string RoomType,
    int Pax,
    decimal TotalPrice,
    int TotalNights,
    string Status,
    DateTime CreatedAt
);
