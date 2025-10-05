

DROP_TABLE = """
DROP TABLE IF EXISTS forest_raw;

"""


CREATE_TABLE_RAW = """ CREATE TABLE IF NOT EXISTS forest_raw (
            Elevation INT NULL,
            Aspect INT NULL,
            Slope INT NULL,
            Horizontal_Distance_To_Hydrology INT NULL,
            Vertical_Distance_To_Hydrology INT NULL,
            Horizontal_Distance_To_Roadways INT NULL,
            Hillshade_9am INT NULL,
            Hillshade_Noon INT NULL,
            Hillshade_3pm INT NULL,
            Horizontal_Distance_To_Fire_Points INT NULL,
            Wilderness_Area VARCHAR(50) NULL,
            Soil_Type VARCHAR(50) NULL,
            Cover_Type INT NULL
        )
        """

