from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from . import clients


class CarsView(APIView):
    def get(self, request):
        show_all = request.query_params.get("showAll") == "true"
        page = int(request.query_params.get("page", 0))
        size = int(request.query_params.get("size", 10))
        cars = clients.get_cars(show_all, page, size)
        return Response(cars)


class RentalListView(APIView):
    def get(self, request):
        username = request.headers.get("X-User-Name")
        rentals = clients.get_rentals(username)

        enriched = []
        for r in rentals:
            car = clients.get_car(r["carUid"])
            payment = clients.get_payment(r["paymentUid"])
            enriched.append({
                "rentalUid": r["rentalUid"],
                "status": r["status"],
                "dateFrom": r["dateFrom"],
                "dateTo": r["dateTo"],
                "car": {
                    "carUid": car["carUid"],
                    "brand": car["brand"],
                    "model": car["model"],
                    "registrationNumber": car["registrationNumber"],
                },
                "payment": {
                    "paymentUid": payment["paymentUid"],
                    "status": payment["status"],
                    "price": payment["price"],
                }
            })
        return Response(enriched)

    def post(self, request):
        username = request.headers.get("X-User-Name")

        car_uid = request.data["carUid"]
        date_from = request.data["dateFrom"]
        date_to = request.data["dateTo"]

        car = clients.get_car(car_uid)
        price_per_day = car["price"]

        from datetime import date
        d1, d2 = date.fromisoformat(date_from), date.fromisoformat(date_to)
        total_days = (d2 - d1).days
        total_price = price_per_day * total_days

        payment = clients.create_payment(total_price)
        clients.reserve_car(car_uid)

        rental = clients.create_rental(username, car_uid, payment["paymentUid"], date_from, date_to)

        return Response({
            "rentalUid": rental["rentalUid"],
            "status": rental["status"],
            "carUid": car_uid,
            "dateFrom": date_from,
            "dateTo": date_to,
            "payment": payment
        }, status=status.HTTP_200_OK)

class RentalDetailView(APIView):
    """GET/DELETE /api/v1/rental/{rentalUid}"""

    def get(self, request, rentalUid):
        username = request.headers.get("X-User-Name")

        r = clients.get_rental(username, str(rentalUid))
        car = clients.get_car(r["carUid"])
        payment = clients.get_payment(r["paymentUid"])
        return Response({
            "rentalUid": r["rentalUid"],
            "status": r["status"],
            "dateFrom": r["dateFrom"],
            "dateTo": r["dateTo"],
            "car": {
                "carUid": car["carUid"],
                "brand": car["brand"],
                "model": car["model"],
                "registrationNumber": car["registrationNumber"],
            },
            "payment": {
                "paymentUid": payment["paymentUid"],
                "status": payment["status"],
                "price": payment["price"],
            }
        })

    def delete(self, request, rentalUid):
        """Отмена аренды: release car + cancel payment + cancel rental → 204"""
        username = request.headers.get("X-User-Name")

        r = clients.get_rental(username, str(rentalUid))

        clients.release_car(r["carUid"])
        clients.cancel_payment(r["paymentUid"])
        clients.cancel_rental(username, str(rentalUid))

        return Response(status=status.HTTP_204_NO_CONTENT)


class RentalFinishView(APIView):
    """POST /api/v1/rental/{rentalUid}/finish"""

    def post(self, request, rentalUid):
        username = request.headers.get("X-User-Name")
        r = clients.get_rental(username, str(rentalUid))

        clients.release_car(r["carUid"])
        clients.finish_rental(username, str(rentalUid))

        return Response(status=status.HTTP_204_NO_CONTENT)