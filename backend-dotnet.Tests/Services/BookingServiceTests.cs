using backend_dotnet.DTOs;
using backend_dotnet.Models;
using backend_dotnet.Repositories;
using backend_dotnet.Services;
using FluentAssertions;
using Microsoft.Extensions.Logging;
using NSubstitute;
using NSubstitute.ExceptionExtensions;
using Xunit;

namespace backend_dotnet.Tests.Services;

public class BookingServiceTests
{
    private readonly IBookingRepository _bookingRepo = Substitute.For<IBookingRepository>();
    private readonly IRoomRepository _roomRepo = Substitute.For<IRoomRepository>();
    private readonly ILogger<BookingService> _logger = Substitute.For<ILogger<BookingService>>();
    private readonly BookingService _sut;

    public BookingServiceTests()
    {
        _sut = new BookingService(_bookingRepo, _roomRepo, _logger);
    }

    [Fact]
    public async Task CreateBookingAsync_ShouldFail_WhenCheckInDateIsInPast()
    {
        // Arrange
        var request = new BookingRequestDto(
            CustomerName: "John Doe",
            CheckInDate: DateTime.UtcNow.AddDays(-2),
            CheckOutDate: DateTime.UtcNow.AddDays(2),
            RoomId: 1,
            Pax: 2
        );

        // Act
        var result = await _sut.CreateBookingAsync(request);

        // Assert
        result.IsSuccess.Should().BeFalse();
        result.StatusCode.Should().Be(400);
        result.Error.Should().Contain("past");
    }

    [Fact]
    public async Task CreateBookingAsync_ShouldFail_WhenCheckOutDateIsBeforeOrEqualToCheckInDate()
    {
        // Arrange
        var checkIn = DateTime.UtcNow.AddDays(5);
        var request = new BookingRequestDto(
            CustomerName: "John Doe",
            CheckInDate: checkIn,
            CheckOutDate: checkIn,
            RoomId: 1,
            Pax: 2
        );

        // Act
        var result = await _sut.CreateBookingAsync(request);

        // Assert
        result.IsSuccess.Should().BeFalse();
        result.StatusCode.Should().Be(400);
        result.Error.Should().Contain("Check-out date must be at least one day after check-in date");
    }

    [Fact]
    public async Task CreateBookingAsync_ShouldFail_WhenNightsExceeds30()
    {
        // Arrange
        var checkIn = DateTime.UtcNow.AddDays(1);
        var checkOut = checkIn.AddDays(31);
        var request = new BookingRequestDto(
            CustomerName: "Long Stay Guest",
            CheckInDate: checkIn,
            CheckOutDate: checkOut,
            RoomId: 1,
            Pax: 2
        );

        // Act
        var result = await _sut.CreateBookingAsync(request);

        // Assert
        result.IsSuccess.Should().BeFalse();
        result.StatusCode.Should().Be(400);
        result.Error.Should().Contain("30 consecutive nights");
    }

    [Fact]
    public async Task CreateBookingAsync_ShouldFail_WhenRoomDoesNotExistOrIsInactive()
    {
        // Arrange
        var request = new BookingRequestDto(
            CustomerName: "John Doe",
            CheckInDate: DateTime.UtcNow.AddDays(2),
            CheckOutDate: DateTime.UtcNow.AddDays(5),
            RoomId: 999,
            Pax: 2
        );

        _roomRepo.GetByIdAsync(999, Arg.Any<CancellationToken>())
            .Returns((Room?)null);

        // Act
        var result = await _sut.CreateBookingAsync(request);

        // Assert
        result.IsSuccess.Should().BeFalse();
        result.StatusCode.Should().Be(400);
        result.Error.Should().Contain("does not exist or is currently inactive");
    }

    [Fact]
    public async Task CreateBookingAsync_ShouldFail_WhenPaxExceedsRoomCapacity()
    {
        // Arrange
        var room = new Room
        {
            Id = 1,
            Name = "Deluxe Ocean Suite",
            Type = "Suite",
            Capacity = 2,
            PricePerNight = 8500m,
            IsActive = true
        };

        var request = new BookingRequestDto(
            CustomerName: "Family Group",
            CheckInDate: DateTime.UtcNow.AddDays(3),
            CheckOutDate: DateTime.UtcNow.AddDays(6),
            RoomId: 1,
            Pax: 4
        );

        _roomRepo.GetByIdAsync(1, Arg.Any<CancellationToken>())
            .Returns(room);

        // Act
        var result = await _sut.CreateBookingAsync(request);

        // Assert
        result.IsSuccess.Should().BeFalse();
        result.StatusCode.Should().Be(400);
        result.Error.Should().Contain("exceeds maximum capacity");
    }

    [Fact]
    public async Task CreateBookingAsync_ShouldFail_WhenRoomIsAlreadyReservedForDates()
    {
        // Arrange
        var checkIn = DateTime.UtcNow.AddDays(3).Date;
        var checkOut = DateTime.UtcNow.AddDays(6).Date;
        var room = new Room
        {
            Id = 1,
            Name = "Grand Azure Villa",
            Type = "Villa",
            Capacity = 4,
            PricePerNight = 18000m,
            IsActive = true
        };

        var request = new BookingRequestDto(
            CustomerName: "VIP Guest",
            CheckInDate: checkIn,
            CheckOutDate: checkOut,
            RoomId: 1,
            Pax: 2
        );

        _roomRepo.GetByIdAsync(1, Arg.Any<CancellationToken>()).Returns(room);
        _roomRepo.IsRoomAvailableAsync(1, checkIn, checkOut, Arg.Any<CancellationToken>())
            .Returns(false);

        // Act
        var result = await _sut.CreateBookingAsync(request);

        // Assert
        result.IsSuccess.Should().BeFalse();
        result.StatusCode.Should().Be(400);
        result.Error.Should().Contain("already reserved");
    }

    [Fact]
    public async Task CreateBookingAsync_ShouldSucceed_WhenAllValidationsPass()
    {
        // Arrange
        var checkIn = DateTime.UtcNow.AddDays(5).Date;
        var checkOut = DateTime.UtcNow.AddDays(8).Date; // 3 nights
        var room = new Room
        {
            Id = 1,
            Name = "Ocean Panorama Villa",
            Type = "Villa",
            Capacity = 4,
            PricePerNight = 12000m,
            IsActive = true
        };

        var request = new BookingRequestDto(
            CustomerName: "Khun Somchai",
            CheckInDate: checkIn,
            CheckOutDate: checkOut,
            RoomId: 1,
            Pax: 2
        );

        _roomRepo.GetByIdAsync(1, Arg.Any<CancellationToken>()).Returns(room);
        _roomRepo.IsRoomAvailableAsync(1, checkIn, checkOut, Arg.Any<CancellationToken>()).Returns(true);

        _bookingRepo.CreateAsync(Arg.Any<Booking>(), Arg.Any<CancellationToken>())
            .Returns(callInfo =>
            {
                var b = callInfo.Arg<Booking>();
                b.Id = 101;
                return b;
            });

        // Act
        var result = await _sut.CreateBookingAsync(request);

        // Assert
        result.IsSuccess.Should().BeTrue();
        result.StatusCode.Should().Be(201);
        result.Value.Should().NotBeNull();
        result.Value!.Id.Should().Be(101);
        result.Value.CustomerName.Should().Be("Khun Somchai");
        result.Value.TotalNights.Should().Be(3);
        result.Value.TotalPrice.Should().Be(36000m); // 3 * 12,000
        result.Value.Status.Should().Be("Confirmed");
    }

    [Fact]
    public async Task GetByIdAsync_ShouldReturnNotFound_WhenBookingDoesNotExist()
    {
        // Arrange
        _bookingRepo.GetByIdAsync(999, Arg.Any<CancellationToken>())
            .Returns((Booking?)null);

        // Act
        var result = await _sut.GetByIdAsync(999);

        // Assert
        result.IsSuccess.Should().BeFalse();
        result.StatusCode.Should().Be(404);
        result.Error.Should().Contain("not found");
    }

    [Fact]
    public async Task GetByIdAsync_ShouldReturnBooking_WhenExists()
    {
        // Arrange
        var checkIn = DateTime.UtcNow.Date;
        var checkOut = checkIn.AddDays(2);
        var booking = new Booking
        {
            Id = 42,
            CustomerName = "Alice Smith",
            CheckInDate = checkIn,
            CheckOutDate = checkOut,
            RoomId = 2,
            Pax = 2,
            TotalPrice = 15000m,
            Status = "Confirmed",
            CreatedAt = DateTime.UtcNow,
            Room = new Room { Id = 2, Name = "Sunset Suite", Type = "Suite" }
        };

        _bookingRepo.GetByIdAsync(42, Arg.Any<CancellationToken>()).Returns(booking);

        // Act
        var result = await _sut.GetByIdAsync(42);

        // Assert
        result.IsSuccess.Should().BeTrue();
        result.Value.Should().NotBeNull();
        result.Value!.Id.Should().Be(42);
        result.Value.RoomName.Should().Be("Sunset Suite");
        result.Value.TotalNights.Should().Be(2);
    }
}
