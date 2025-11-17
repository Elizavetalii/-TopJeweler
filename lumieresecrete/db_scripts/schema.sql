-- Таблица ролей
CREATE TABLE Roles (
  RoleID SERIAL PRIMARY KEY,
  RoleName VARCHAR(255) NOT NULL
);

-- Таблица пользователей
CREATE TABLE Users (
  UserID SERIAL PRIMARY KEY,
  FirstName VARCHAR(255) NOT NULL,
  LastName VARCHAR(255) NOT NULL,
  Email VARCHAR(255) UNIQUE NOT NULL,
  Password VARCHAR(255) NOT NULL,
  CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  LastLogin TIMESTAMP,
  RoleID INT REFERENCES Roles(RoleID) ON DELETE SET NULL
);

-- UserSettings table
CREATE TABLE UserSettings (
  UserSettingID SERIAL PRIMARY KEY,
  Theme theme_enum DEFAULT 'light',
  DateFormat VARCHAR(20),
  PageSize INT,
  SavedFilters JSON,
  UserID INT REFERENCES Users(UserID) ON DELETE CASCADE
);

-- SessionLog table
CREATE TABLE SessionLog (
  SessionLogID SERIAL PRIMARY KEY,
  UserID INT REFERENCES Users(UserID) ON DELETE CASCADE,
  LoginTime TIMESTAMP,
  LogoutTime TIMESTAMP
);

-- AuditLog table
CREATE TABLE AuditLog (
  AuditLogID SERIAL PRIMARY KEY,
  TableName VARCHAR(255),
  Operation VARCHAR(255),
  Datetime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  OldValue VARCHAR(255),
  NewValue VARCHAR(255),
  Field VARCHAR(255),
  UserID INT REFERENCES Users(UserID) ON DELETE SET NULL
);

-- Backups table
CREATE TABLE Backups (
  BackupID SERIAL PRIMARY KEY,
  CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  Type VARCHAR(255),
  FilePath TEXT,
  Status VARCHAR(100),
  UserID INT REFERENCES Users(UserID) ON DELETE SET NULL
);

-- Address table
CREATE TABLE Address (
  AddressID SERIAL PRIMARY KEY,
  City VARCHAR(255),
  Street VARCHAR(255)
);

-- Stores table
CREATE TABLE Stores (
  StoreID SERIAL PRIMARY KEY,
  Name VARCHAR(255),
  AddressID INT REFERENCES Address(AddressID) ON DELETE SET NULL,
  BusinessHours VARCHAR(255),
  Photo TEXT
);

-- Categories table
CREATE TABLE Categories (
  CategoryID SERIAL PRIMARY KEY,
  Name VARCHAR(255)
);

-- Products table
CREATE TABLE Products (
  ProductID SERIAL PRIMARY KEY,
  Name VARCHAR(255),
  CategoryID INT REFERENCES Categories(CategoryID) ON DELETE SET NULL
);

-- Colors table
CREATE TABLE Colors (
  GemstoneID SERIAL PRIMARY KEY,
  NameColor VARCHAR(255),
  ColorCode VARCHAR(100)
);

-- Sizes table
CREATE TABLE Sizes (
  SizeID SERIAL PRIMARY KEY,
  Size VARCHAR(100)
);

-- ProductVariant table
CREATE TABLE ProductVariant (
  ProductVariantID SERIAL PRIMARY KEY,
  ProductID INT REFERENCES Products(ProductID) ON DELETE CASCADE,
  ColorID INT REFERENCES Colors(GemstoneID) ON DELETE SET NULL,
  SizeID INT REFERENCES Sizes(SizeID) ON DELETE SET NULL,
  Structure VARCHAR(100),
  Price DECIMAL(10,2),
  Photo TEXT,
  Description TEXT,
  Quantity INT,
  StoreID INT REFERENCES Stores(StoreID) ON DELETE SET NULL
);

-- Status table
CREATE TABLE Status (
  StatusID SERIAL PRIMARY KEY,
  NameStatus VARCHAR(255)
);

-- Orders table
CREATE TABLE Orders (
  OrderID SERIAL PRIMARY KEY,
  UserID INT REFERENCES Users(UserID) ON DELETE SET NULL,
  CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  StatusID INT REFERENCES Status(StatusID) ON DELETE SET NULL,
  TotalAmount DECIMAL(10,2),
  StoreID INT REFERENCES Stores(StoreID) ON DELETE SET NULL
);

-- OrderItems table
CREATE TABLE OrderItems (
  OrderItemID SERIAL PRIMARY KEY,
  OrderID INT REFERENCES Orders(OrderID) ON DELETE CASCADE,
  ProductVariantID INT REFERENCES ProductVariant(ProductVariantID) ON DELETE CASCADE,
  Quantity INT,
  Price DECIMAL(10,2)
);

-- CartItems table
CREATE TABLE CartItems (
  OrderItemID SERIAL PRIMARY KEY,
  UserID INT REFERENCES Users(UserID) ON DELETE CASCADE,
  ProductVariantID INT REFERENCES ProductVariant(ProductVariantID) ON DELETE CASCADE,
  Quantity INT,
  Price DECIMAL(10,2)
);

-- Payments table
CREATE TABLE Payments (
  PaymentID SERIAL PRIMARY KEY,
  OrderID INT REFERENCES Orders(OrderID) ON DELETE CASCADE,
  Method VARCHAR(100),
  Amount DECIMAL(10,2),
  Status VARCHAR(100)
);