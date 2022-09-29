ecglib: EcgQualityCheck.so

# Link
EcgQualityCheck.so: EcgQualityCheck.o
	g++ -shared -o $@ $^

# Compile
EcgQualityCheck.o: EcgQualityCheck.cpp EcgQualityCheck.h
	g++ -std=c++11 -fPIC -c $<

.PHONY: clean
clean:
	@rm -f *.o *.so