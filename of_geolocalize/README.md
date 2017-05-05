# of_geolocalize #

of_geolocalize is a module made to add GPS coordinates to partners and companies, in order to display them on a map.  
Said GPS coordinates can be obtained through geocoding of addresses using Nominatim, or allocated manually.  

## Features ##

* Adds a geolocation tab to partners and companies form view.  
* Partners geolocation tab allow to geocode their addresses, set coordinates manually and reset geo fields. Also displays data about Nominatim input and output in debug mode.  
* Companies geolocation tab allow to geocode their addresses and their partners addresses (different modes are possible to use). Also displays stats about the current state of their partners geocoding.  
* 2 geocoding modes, a faster and a greedier.  
	The faster takes the address as is and should be used on first attempt of geocoding partners.  
	The greedier works a bit on street and street2 fields and may request Nominatim several times for a single address.  
* Adds a list view designed to help locating partners for whom geocoding failed.  
	this view displays coordinates and addresses.  
	modifying an address will cause geocoding to be tried again.  
	modifying GPS coordinates will set the partner's geocoding to 'manual', which will prevent geocoding to be tried again for this partner.  
	special filters to visibility on partners state of geocoding are added to this list view  

## Usage ##

After installation of the module, first thing we need to do is to set the Nominatim server base URL.  
To do so, go to Configuration -> Parameters -> System Parameters and change the value of Nominatim_Base_URL  
	the URL should look something like <your geocoding server address>/nominatim/search  

Now we can start geocoding !  
Go to (one of) your company(ies) geolocation tab.  
Click on 'Geolocate Partners', choose 'Try to geocode all partners not tried yet' and validate.  
The process can take a long time.  
When its finished, there will most likely be partners for whom geocoding failed.  
Click on 'Geolocate Partners', choose 'Try to geocode all partners not yet localized' and validate.  
The process takes an even longer time per partner.  
If there are still partners for whom geocoding failed on second attempt, this means the geocoding server was not able to find the address in the database.  
Click on 'Geolocate Partners', choose 'Fetch partners who miss geolocation' and validate.  
We get a list view with partners GPS coordinates and addresses.
From there we can either modify the address (that will trigger a new attempt at geocoding the address) or set the coordinates ourselves.  

This list view is also accessible through Sales -> Configuration -> Contacts -> Partners Geolocation

if you want to deactivate geocoding on creation of a partner (in case of import for example):
go to configuration -> Parameters -> System Parameters and change the value of Deactivate_Geocoding_On_Create
Any value other than "0" will deactivate geocoding on creation of a partner

