using backend_dotnet.Data;
using backend_dotnet.Repositories;
using backend_dotnet.Services;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);

// 1. Database Connection Configuration
if (builder.Environment.IsEnvironment("Testing"))
{
    builder.Services.AddDbContext<HotelDbContext>(options =>
    {
        options.UseInMemoryDatabase("HotelTestingDb");
    });
}
else
{
    var connectionString = builder.Configuration.GetConnectionString("DefaultConnection")
        ?? Environment.GetEnvironmentVariable("DB_CONNECTION_STRING")
        ?? "Server=localhost;Port=3306;Database=hotel_db;User=hotel_user;Password=hotel_pass_2026;";

    builder.Services.AddDbContext<HotelDbContext>(options =>
    {
        options.UseMySQL(connectionString);
    });
}

// 2. Dependency Injection (Repositories & Services)
builder.Services.AddScoped<IRoomRepository, RoomRepository>();
builder.Services.AddScoped<IBookingRepository, BookingRepository>();
builder.Services.AddScoped<IRoomService, RoomService>();
builder.Services.AddScoped<IBookingService, BookingService>();

// 3. Controllers & OpenAPI 3.1
builder.Services.AddControllers();
builder.Services.AddOpenApi(options =>
{
    options.OpenApiVersion = Microsoft.OpenApi.OpenApiSpecVersion.OpenApi3_1;
});

// 4. CORS Policy
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAll", policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyHeader()
              .AllowAnyMethod();
    });
});

var app = builder.Build();

// 5. Middleware Pipeline
if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

app.UseCors("AllowAll");
app.UseAuthorization();
app.MapControllers();

// Healthcheck endpoint
app.MapGet("/health", () => Results.Ok(new { status = "Healthy", service = "Hotel.Backend.DotNet10", timestamp = DateTime.UtcNow }));

// 6. Automatic Database Initialization & Seeding on Startup
var logger = app.Services.GetRequiredService<ILogger<Program>>();
try
{
    await DbInitializer.InitializeDatabaseAsync(app.Services, logger);
}
catch (Exception ex)
{
    logger.LogWarning(ex, "Database auto-migration skipped or failed during startup. The application will continue running.");
}

app.Run();

public partial class Program { }
