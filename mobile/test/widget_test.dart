import 'package:dawa/widgets/pharmacie_carte.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('formatPrix groupe les milliers', () {
    expect(formatPrix(500), '500 FC');
    expect(formatPrix(4500), '4 500 FC');
    expect(formatPrix(125000), '125 000 FC');
  });

  test('formatDistance', () {
    expect(formatDistance(0.15), '150 m');
    expect(formatDistance(2.54), '2,5 km');
  });
}
