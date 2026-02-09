import 'package:flutter/material.dart';
import '../services/api_service.dart';

class AuthProvider extends ChangeNotifier {
  final ApiService _api;
  bool _isLoggedIn = false;
  String? _childId;
  String? _familyId;
  String? _childName;

  AuthProvider(this._api);

  bool get isLoggedIn => _isLoggedIn;
  String? get childId => _childId;
  String? get familyId => _familyId;
  String? get childName => _childName;

  Future<void> checkAuth() async {
    _isLoggedIn = await _api.isLoggedIn();
    notifyListeners();
  }

  Future<bool> login(String email, String password) async {
    try {
      await _api.login(email, password);
      _isLoggedIn = true;
      notifyListeners();
      return true;
    } catch (e) {
      _isLoggedIn = false;
      notifyListeners();
      return false;
    }
  }

  void setChildInfo(String childId, String familyId, String name) {
    _childId = childId;
    _familyId = familyId;
    _childName = name;
    notifyListeners();
  }

  Future<void> logout() async {
    await _api.logout();
    _isLoggedIn = false;
    _childId = null;
    _familyId = null;
    _childName = null;
    notifyListeners();
  }
}
