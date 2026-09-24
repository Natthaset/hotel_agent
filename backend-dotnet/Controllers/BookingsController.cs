using backend_dotnet.DTOs;
using backend_dotnet.Services;
using Microsoft.AspNetCore.Mvc;

namespace backend_dotnet.Controllers;

[ApiController]
[Route("api/v1/[controller]")]
[Produces("application/json")]
public class BookingsController(IBookingService bookingService, ILogger<BookingsController> logger) : ControllerBase
{
    /// <summary>
    /// Create a new hotel room booking.
    /// </summary>
    [HttpPost]
    [ProducesResponseType(typeof(BookingResponseDto), StatusCodes.Status201Created)]
    [ProducesResponseType(typeof(ProblemDetails), StatusCodes.Status400BadRequest)]
    [ProducesResponseType(typeof(ProblemDetails), StatusCodes.Status500InternalServerError)]
    public async Task<IActionResult> CreateBooking([FromBody] BookingRequestDto request, CancellationToken ct)
    {
        if (!ModelState.IsValid)
        {
            return BadRequest(ModelState);
        }

        logger.LogInformation("Processing booking request for {CustomerName}, RoomId={RoomId}", request.CustomerName, request.RoomId);
        var result = await bookingService.CreateBookingAsync(request, ct);

        if (!result.IsSuccess)
        {
            return StatusCode(result.StatusCode, new ProblemDetails
            {
                Status = result.StatusCode,
                Title = "Booking Failed",
                Detail = result.Error
            });
        }

        return CreatedAtAction(nameof(GetById), new { id = result.Value!.Id }, result.Value);
    }

    /// <summary>
    /// Retrieve booking details by booking ID.
    /// </summary>
    [HttpGet("{id:int}")]
    [ProducesResponseType(typeof(BookingResponseDto), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ProblemDetails), StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetById(int id, CancellationToken ct)
    {
        var result = await bookingService.GetByIdAsync(id, ct);
        if (!result.IsSuccess)
        {
            return StatusCode(result.StatusCode, new ProblemDetails
            {
                Status = result.StatusCode,
                Title = "Booking Not Found",
                Detail = result.Error
            });
        }

        return Ok(result.Value);
    }
}
