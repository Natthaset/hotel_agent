using backend_dotnet.DTOs;
using backend_dotnet.Services;
using Microsoft.AspNetCore.Mvc;

namespace backend_dotnet.Controllers;

[ApiController]
[Route("api/v1/[controller]")]
[Produces("application/json")]
public class RoomsController(IRoomService roomService, ILogger<RoomsController> logger) : ControllerBase
{
    /// <summary>
    /// Search available rooms by date range and optional room type.
    /// </summary>
    [HttpGet("availability")]
    [ProducesResponseType(typeof(List<RoomDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ProblemDetails), StatusCodes.Status400BadRequest)]
    [ProducesResponseType(typeof(ProblemDetails), StatusCodes.Status500InternalServerError)]
    public async Task<IActionResult> GetAvailability(
        [FromQuery] DateTime? checkIn,
        [FromQuery] DateTime? checkOut,
        [FromQuery] string? roomType,
        CancellationToken ct)
    {
        logger.LogInformation("Checking room availability: checkIn={CheckIn}, checkOut={CheckOut}, roomType={RoomType}", checkIn, checkOut, roomType);
        var result = await roomService.GetAvailableRoomsAsync(checkIn, checkOut, roomType, ct);

        if (!result.IsSuccess)
        {
            return StatusCode(result.StatusCode, new ProblemDetails
            {
                Status = result.StatusCode,
                Title = "Room Availability Request Failed",
                Detail = result.Error
            });
        }

        return Ok(result.Value);
    }

    /// <summary>
    /// Get details of a specific room by its ID.
    /// </summary>
    [HttpGet("{id:int}")]
    [ProducesResponseType(typeof(RoomDto), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ProblemDetails), StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetById(int id, CancellationToken ct)
    {
        var result = await roomService.GetByIdAsync(id, ct);
        if (!result.IsSuccess)
        {
            return StatusCode(result.StatusCode, new ProblemDetails
            {
                Status = result.StatusCode,
                Title = "Room Not Found",
                Detail = result.Error
            });
        }

        return Ok(result.Value);
    }
}
